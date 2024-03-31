import re
import requests
import json
import time
import articleparser

#### Const Variables ####

# Prompt to Generate Formal Answer
FORMAL_ANSWER_PROMPT = """Rewrite the Answer to Formal Answer according to the Question. Don't Exclude or Modify anything from Target Answer,
Example:
Q: Who is Iron Man?
A: Tony Stark
FA: Tony Stark is Iron Man.

Target:
Q: {}
A: {}
FA:"""

# API Key of Hugging Face
HuggingFace_APIKey = ""

# Serper API Key
Serper_APIKey = ""

######## Functions to add the API Keys ########
# Set Hugging Face API Key


def setHuggingFaceApiKey(apiKey: str):
    global HuggingFace_APIKey
    if (apiKey == ""):
        raise ValueError("APIKey Cannot be Empty")

    HuggingFace_APIKey = apiKey


# Set Serper API Key
def setSerperApiKey(apiKey: str):
    global Serper_APIKey
    if (apiKey == ""):
        raise ValueError("APIKey Cannot be Empty")

    Serper_APIKey = apiKey

######## Utility Functions ########
# Parse Articles from Search Results


def parseArticlesFromSearchResults(searchResults, parseArticles=True, timeout=10, printProgress=False):
    articles = []
    for i, item in enumerate(searchResults):
        try:
            if (parseArticles):
                articleData = articleparser.parseArticle(
                    item["url"], timeout=timeout)
                if (articleData is None):
                    article = f"{item['title']}\n{item['description']}"
                else:
                    article = articleData["content"]
            else:
                article = f"{item['title']}\n{item['description']}"

            articles.append(article)
            if (printProgress):
                print("Article Parsed:", i + 1, flush=1)
        except Exception as e:
            pass

    return articles


# Check if article contains the Description
def articleContainsDesc(article: str, description: str):
    # Replace more than 2 continuous dots with ".+"
    pattern = re.sub(r'(\\\.){3,}', r".+", re.escape(description))
    matches = re.findall(pattern, article, re.MULTILINE)

    return len(matches) > 0


# Trim the article
def getTrimmedText(article: str, description: str, article_length: int):
    pattern = re.compile(re.sub(r'(\\\.){3,}', r".+", re.escape(description)))
    found = pattern.search(article)
    if not (found):
        return article[:article_length]

    d_index = found.span()[0]

    s_length = (article_length - d_index + len(description)) // 2
    e_length = s_length

    s_index = d_index - s_length
    if (s_index < 0):
        s_index = 0

    e_index = s_index + s_length + len(description) + e_length

    trimmedText = article[s_index:e_index]
    # filtering to avoid cutout texts...
    filteredText = " ".join(trimmedText.split(" ")[1:-2])

    return filteredText


# Combine all the articles as One
def combineArticles(articles: list, searchResults: list, min_article_length=3000, max_combine_length=15000, filter=True):

    average_article_length = len(articles) // max_combine_length
    if (average_article_length < min_article_length):
        average_article_length = min_article_length

    articleDataSet = []
    for article, searchResult in zip(articles, searchResults):
        if ((not articleContainsDesc(article, searchResult["description"])) and (filter)):
            continue

        trimmed = "Title: " + searchResult["title"] + "\nDescription: " + searchResult["description"] + \
            "\nBody: " + \
            getTrimmedText(
                article, searchResult["description"], average_article_length)
        articleDataSet.append(trimmed)

    articleData = "\n\n".join(articleDataSet)
    return articleData


######## AI Parsing Functions ########

# Get the Answer from Context
def getAIQuestionAnswer(context, question, modelIndex=0):
    MODELS = ["https://api-inference.huggingface.co/models/deepset/roberta-base-squad2",
              "https://api-inference.huggingface.co/models/twmkn9/distilbert-base-uncased-squad2"]

    headers = {"Authorization": "Bearer " + HuggingFace_APIKey}
    payload = {"inputs": {
        "question": question,
        "context": context
    }}

    response = requests.post(MODELS[modelIndex], headers=headers, json=payload)

    result = response.json()
    if (type(result) == list):
        result = result[0]

    while ("error" in result.keys()):
        if (all(x in result["error"].lower() for x in ["model", "loading"])):
            time.sleep(result["estimated_time"] / 1000)
            result = response.json()
            if (type(result) == list):
                result = result[0]
        else:
            return {"success": False, "result": result}

    if ("answer" not in result.keys()):
        return {"success": False, "result": result}

    return {"success": True, "result": result}


# Convert easy answer tot Formal Answer. This one is Optional
def getAIFormalAnswer(question, answer):
    prompt = FORMAL_ANSWER_PROMPT.format(question, answer)

    API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-xxl"

    headers = {"Authorization": "Bearer " + HuggingFace_APIKey}
    payload = {"inputs": prompt}

    response = requests.post(API_URL, headers=headers, json=payload)

    result = response.json()
    if (type(result) == list):
        result = result[0]

    while ("error" in result.keys()):
        if (all(x in result["error"].lower() for x in ["model", "loading"])):
            time.sleep(result["estimated_time"] / 1000)
            result = response.json()
            if (type(result) == list):
                result = result[0]
        else:
            return {"success": False, "result": result}

    if ("generated_text" not in result.keys()):
        return {"success": False, "result": result}

    return {"success": True, "result": result}


######## Answer Via Google Search Functions ########

# Function to get the Answer after AI finished Parsing
def getAIAnswer(question: str, searchResults, preParsedArticles=None, timeout=10, parseArticles=True, preParsedAnswer=None, filter=False, modelIndex=0, printProgress=False):
    """
    Description: Takes `Question` and `Search Results` as Required Input
    Generates Answer using Article parsing and AI
    Parameters:
        question: User Question
        searchResults: Search Results of the Question Searched
        timeout: Timeout of Article URL Request (Default: 10s)
        parseArticles: Parse Article of Every URL and Use it as Description (Default: True)
        preParsedAnswer: If the Answer is already parsed via other source but Still want to Be accurate, so parse the answer via this parameter (Default: None)
        filter: Filter the Articles to contain the Searched Description (Default: False)
        modelIndex: Use the corresponding QnA Model (Default: 0)
        printProgress: Print the progress of the Executions (Default: False)
    """
    getAIAnswer.searchResults = searchResults

    if (preParsedArticles is None):
        articles = parseArticlesFromSearchResults(
            searchResults, parseArticles=parseArticles, timeout=timeout, printProgress=printProgress)
    else:
        articles = preParsedArticles

    getAIAnswer.articles = articles
    if (parseArticles):
        combinedArticle = combineArticles(
            articles, searchResults, filter=filter)
    else:
        combinedArticle = "\n\n".join(articles)

    if (preParsedAnswer):
        combinedArticle = preParsedAnswer + "\n\n" + combinedArticle

    getAIAnswer.combinedArticle = combinedArticle

    answerOutput = getAIQuestionAnswer(
        combinedArticle, question, modelIndex=modelIndex)
    if (not answerOutput["success"]):
        return answerOutput

    getAIAnswer.answerOutput = answerOutput
    if (printProgress):
        print("\nAnswer Parsed\n", flush=1)

    formalAnswerOutput = getAIFormalAnswer(
        question, answerOutput["result"]["answer"])
    if (not formalAnswerOutput["success"]):
        return formalAnswerOutput

    getAIAnswer.formalAnswerOutput = formalAnswerOutput
    if (printProgress):
        print("Formal Answer Parsed\n", flush=1)

    formalAnswer = formalAnswerOutput["result"]["generated_text"]
    getAIAnswer.formalAnswer = formalAnswer

    return {"success": True, "result": formalAnswer}


# Get the Answer via Parsing Search URLs using GoogleSearch_Python
def getAnswerViaGoogleSearch(question: str, num_results=3, timeout=10, filter=False, modelIndex=0, printProgress=False):
    """
    Description: Get Question's answer Google Search
    Parameters:
        question: Actual Question
        num_results: Number of results to parse Article from (Default: 3)
        timeout: Timeout of Article URL Request (Default: 10s)
        filter: Filter the Articles by the Search Result Descriptions [Not Recommended] (Default: False)
        modelIndex: Use the corresponding QnA Model (Default: 0)
        printProgress: Print the progress of the Executions (Default: False)
    """
    if (HuggingFace_APIKey == ""):
        raise ValueError(
            "You must Assign your Hugging Face API Key First!\nUse: `setHuggingFaceApiKey(apiKey)` to Assign")

    searchResults = articleparser.getGoogleSearchResults(
        query=question, num_results=num_results)
    answerOutput = getAIAnswer(question, searchResults, timeout=timeout,
                               filter=filter, modelIndex=modelIndex, printProgress=printProgress)

    getAnswerViaGoogleSearch.answerOutput = answerOutput
    return answerOutput


######## Answer Via using Serper API Functions (Requires API Key) ########

# Parse Search Results to a Similar Format of Google Search
def formatSerperSearchResults(serperSearchResults):
    searchResults = []
    for result in serperSearchResults:
        searchResults.append({
            "title": result["title"],
            "url": result["link"],
            "description": result["snippet"]
        })

    return searchResults

# Parser the Automated Serper Answer


def parseSerperApiAnswer(searchResults: dict):
    if ("answerBox" not in searchResults.keys()):
        return None

    answerBox = searchResults["answerBox"]
    answer = {
        "title": answerBox["title"]
    }
    if ("answer" in answerBox.keys()):
        answer["answer"] = answerBox["answer"]
    elif ("snippet" in answerBox.keys()):
        if ("snippetHighlighted" in answerBox.keys()):

            answer["answer"] = answerBox["snippetHighlighted"][0]
        else:
            answer["answer"] = answerBox["snippet"]

    return answer


# Get Serper API result
def getSerperApiResult(query):
    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": query
    })
    headers = {
        "X-API-KEY": Serper_APIKey,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=payload)
    apiResults = response.json()

    return apiResults

# Get The answer using Serper API


def getAnswerViaSerperApi(question: str, num_results=3, timeout=10, forceAi=False, fast=True, modelIndex=0, printProgress=False):
    """
    Description: Get Question's answer using Serper API.
    Return:
            If Success: {"success": True, "result": AnswerData}
            If Unsuccess: {"success": False, "result": ContainingErrorData}
    Parameters:
        question: Actual Question
        num_results: Number of results to parse Article from (Default: 3)
        timeout: Timeout of Article URL Request (Default: 10s)
        forceAi: Force AI Parsing even if Answer Found using Serper API [Slow] (Default: False)
        fast: If forceAi is `True` and fast is also `False`, Will parse all the link's Article first before using Ai parse. And if `False`, then it will use the Serper descriptions. This Param Does not matter if forceAi = False (Default: True)
        modelIndex: Use the corresponding QnA Model (Default: 0)
        printProgress: Print the progress of the Executions (Default: False)
    """
    if (Serper_APIKey == ""):
        raise ValueError(
            "You must Assign your Serper API Key First!\nUse: `setSerperApiKey(apiKey)` to Assign")

    if (HuggingFace_APIKey == ""):
        raise ValueError(
            "You must Assign your Hugging Face API Key First!\nUse: `setHuggingFaceApiKey(apiKey)` to Assign")

    apiResults = getSerperApiResult(question)
    getAnswerViaSerperApi.apiResults = apiResults

    organicSearches = apiResults["organic"]

    searchResults = formatSerperSearchResults(organicSearches)
    getAnswerViaSerperApi.searchResults = searchResults

    if (printProgress):
        print("API Results Parsed\n", flush=1)

    directAnswer = parseSerperApiAnswer(apiResults)
    getAnswerViaSerperApi.directAnswer = directAnswer

    if (printProgress):
        print("Direct Answer Parsed\n", flush=1)

    if (directAnswer is not None) and (not forceAi):
        answerOutput = getAIFormalAnswer(question, directAnswer["answer"])
        if (answerOutput["success"]):
            answerOutput["result"] = answerOutput["result"]["generated_text"]

        getAnswerViaSerperApi.formalAnswerOutput = answerOutput
        if (printProgress):
            print("Formal Answer parsed\n", flush=1)

    elif (directAnswer is not None) and (forceAi):
        answerOutput = getAIAnswer(question, searchResults[:num_results], timeout=timeout, parseArticles=(
            not fast), preParsedAnswer=f"{directAnswer['title']} - {directAnswer['answer']}", printProgress=printProgress)
        if (printProgress):
            print("AI Answer Parsed with Direct Answer\n", flush=1)
    else:
        answerOutput = getAIAnswer(
            question, searchResults[:num_results], timeout=timeout, modelIndex=modelIndex, printProgress=printProgress)
        if (printProgress):
            print("Regular (Full) Answer parsed\n", flush=1)

    getAnswerViaSerperApi.answerOutput = answerOutput
    getAnswerViaSerperApi.getAIAnswer = getAIAnswer

    return answerOutput


# A Class to use the options separately
class GetQuestionAnswer:
    """
    Description: This is a Object Definition of the Answer Getting Process. To use the Functions when Pleased
    Initial Parameters:
        parseType: `search` or `serper` (Default: search)
        num_results: Number of results to parse Article from (Default: 3)
        timeout: Timeout of Article URL Request (Default: 10s)
        parseArticle: If `serper` used and argument is `True`, Will parse all the link's Article first before using Ai parse. And if `False`, then it will use the Serper descriptions. This Param Does not matter if forceAi = False (Default: True)
        modelIndex: Use the corresponding QnA Model (Default: 0)
        printProgress: Print the progress of the Executions (Default: False)
        forceAi: Forcefully use AI even the Serper gives answer First (Default: False)
    """

    question = None

    parseType = None
    num_results = None
    timeout = None
    parseArticle = None
    searchResults = None
    serperResults = None
    serperDirectAnswer = None
    parsedArticles = None
    fotceAi = None
    finalAnswer = None

    # Initialize the Object with Parse Type: "search" or "serper"
    def __init__(self, parseType="search", num_results=5, timeout=10, parseArticle=True, modelIndex=0, forceAi=False) -> None:
        if (parseType not in ["search", "serper"]):
            raise ValueError(
                "parseType can only be either `search` or `serper`")

        if (HuggingFace_APIKey == ""):
            raise ValueError(
                "You must Assign your Hugging Face API Key First!\nUse: `setHuggingFaceApiKey(apiKey)` to Assign")

        if (Serper_APIKey == "") and (parseType == "serper"):
            raise ValueError(
                "You must Assign your Serper API Key First!\nUse: `setSerperApiKey(apiKey)` to Assign")

        self.parseType = parseType
        self.num_results = num_results
        self.timeout = timeout
        self.parseArticle = parseArticle
        self.modelIndex = modelIndex
        self.forceAi = forceAi

    # Search Question Based on the given Question
    def searchQuestion(self, question: str):
        """
        Description: Search in the Web or use Serper api to get the relevant Search Results of given Question
        Parameters:
            question: Your Question
        """
        self.question = question

        if (self.parseType == "search"):
            self.searchResults = articleparser.getGoogleSearchResults(
                query=question, num_results=self.num_results)
            return

        # Else Parser Serper API
        self.serperResults = getSerperApiResult(query=question)

        searchData = self.serperResults["organic"]
        self.searchResults = formatSerperSearchResults(
            searchData)
        self.serperDirectAnswer = parseSerperApiAnswer(self.serperResults)

    # Parse Articles from Search Results

    def parseArticles(self, question=None):
        """
        Description: Parse the Articles from Search Results
        Parameters:
            question (optional): If you want to skip calling `searchAnswer` method, just pass the Question in this method's `question` parameter
        """
        if (self.searchResults is None) and (question is None):
            raise ChildProcessError("You must `searchResult` First!")
        elif (self.searchResults is None) and (question):
            self.searchQuestion(question)

        self.parsedArticles = parseArticlesFromSearchResults(self.searchResults[:self.num_results], parseArticles=(
            self.serperDirectAnswer is None), timeout=self.timeout, printProgress=False)

    # Get the Final Answer
    def getFinalAnswer(self, question=None):
        """
        Description: Get the Final Output answer. Will Return the Answer as Dictionary
        Return:
            If Success: {"success": True, "result": AnswerData}
            If Unsuccess: {"success": False, "result": ContainingErrorData}
        Parameters:
            question (optional): If you want to skip calling `searchAnswer` and `parseArticles` method, just pass the Question in this method's `question` parameter
        """
        if (self.searchResults is None) and (question is None):
            raise ChildProcessError("You must `searchResult` First!")
        elif (self.searchResults is None) and (question):
            self.parseArticles(question)

        if (self.parseType == "search"):
            self.finalAnswer = getAIAnswer(self.question, self.searchResults, preParsedArticles=self.parsedArticles,
                                           timeout=self.timeout, filter=False, modelIndex=self.modelIndex, printProgress=False)

            return self.finalAnswer

        # Else Parser Serper Result
        if (self.serperDirectAnswer is not None) and (not self.forceAi):
            answerOutput = getAIFormalAnswer(
                self.question, self.serperDirectAnswer["answer"])
            if (answerOutput["success"]):
                answerOutput["result"] = answerOutput["result"]["generated_text"]

        elif (self.serperDirectAnswer is not None) and (self.forceAi):
            answerOutput = getAIAnswer(self.question, self.searchResults[:self.num_results], preParsedArticles=self.parsedArticles, timeout=self.timeout,
                                       parseArticles=self.parseArticle, preParsedAnswer=f"{self.serperDirectAnswer['title']} - {self.serperDirectAnswer['answer']}", printProgress=False)
        else:
            answerOutput = getAIAnswer(self.question, self.searchResults[:self.num_results], preParsedArticles=self.parsedArticles,
                                       timeout=self.timeout, parseArticles=self.parseArticle, modelIndex=self.modelIndex, printProgress=False)

        self.finalAnswer = answerOutput
        return self.finalAnswer


######## Testing Purpose Functions ########

# Check the API Keys
def checkApiKeys():
    import os

    global HuggingFace_APIKey, Serper_APIKey
    huggingFaceApi = os.environ.get('HUGGINFACE_API')
    serperApi = os.environ.get('SERPER_API')

    if (huggingFaceApi is None):
        print("Please add Hugging Face Api key as your ENV Variable First using Key `HUGGINFACE_API`")
        exit()

    else:
        HuggingFace_APIKey = huggingFaceApi

    if (serperApi is not None):
        Serper_APIKey = serperApi


# For Test Purpose (Functional)
def main_functional():
    question = input("\nEnter your Question:> ")
    if (question == ""):
        print("\nQuestion cannot be Blank!")
        exit()

    if (Serper_APIKey is None):
        print("\nUsing GoogleSearch Method. You can Use Serper Api for good result. Add Serper API Key in ENV Variable via `SERPER_API`")

        answerData = getAnswerViaGoogleSearch(question)
    else:
        print("\nUsing Serper API")
        answerData = getAnswerViaSerperApi(question)

    if (not answerData["success"]):
        print("\nError Occurred while Getting Answer: ")
        print(answerData)
        exit()

    answer = answerData["result"]
    print("\nAnswer:", answer)


# For Test Purpose (Object)
def main_object():
    question = input("\nEnter your Question:> ")
    if (question == ""):
        print("\nQuestion cannot be Blank!")
        exit()

    getQuestionAnswer = GetQuestionAnswer(
        parseType="search" if Serper_APIKey is None else "serper")

    # Searching for Question
    print("\nSearching for Question")
    getQuestionAnswer.searchQuestion(question)

    # Parsing the Articles
    print("\nParsing the Articles")
    getQuestionAnswer.parseArticles()

    # Parsing the Answer
    print("\nParsing the Answer")
    answerData = getQuestionAnswer.getFinalAnswer()

    if (not answerData["success"]):
        print("\nError Occurred while Getting Answer: ")
        print(answerData)
        exit()

    answer = answerData["result"]
    print("\nAnswer:", answer)


if (__name__ == "__main__"):
    import sys

    try:
        parseType = sys.argv[1]
    except:
        parseType = "function"

    checkApiKeys()
    if (parseType == "object"):
        main_object()
    else:
        main_functional()

# Up-To-Date Question Answer

Get updated Answer of Your Questions!

### Features:

- Answer via Up to date Data

### Use Case:

- Main File Created as a Package / Library which can be used By Importing
- Root's `main.py` file contains Stremlit Example

### Workflow:

- For Direct Google Search

  - Uses [ArticleParser](https://github.com/TheProjectsX/ArticleParser) to Parse Articles from WEB according to Given Question
  - Uses Serverless Hugging Face Model API to get the Answer
  - Uses another Model to Format the Answer to Formal Version
  - Requires Hugging Face API Key

- Using Serper API
  - Uses [Serper](https://serper.dev/) API to parse Search Results
  - Sometimes Serper API gives Answer in the Response. In those cases We Directly use Answer from the Serper API Response
  - Ans if Answer is not Provided, we again use `ArticleParser` to parse the Articles, then use Hugging Face Model to get the Answer.
  - Lastly Uses another Model to Format the Answer to Formal Version
  - Requires Hugging Face and Serper API Keys

### Why using Double models?

The first Idea was to use a Model locally, not via using API. But I did used it in the last.
The QnA model is small, can be used locally if wanted (will update code to do that too!). But the Formal Answer converter uses a Large model, which is Just an Optional approach. We can run it without the Large model too, that's why...

### Limitations:

- Direct Google Search

  - Right now, the Direct Google search version gives false information sometimes.
  - But increasing the Number of Search Results most of the times gives Right Answer.
  - This process is Time Consuming

- Serper API

  - Up to now, no disadvantages found except it Needs API Key

- Can only answer as QnA (Under one line answer). Can't answer correctly for the Questions which needs Explanations...

### Motivation for this Project:

Nothing... Just felt like to create it, so Did!

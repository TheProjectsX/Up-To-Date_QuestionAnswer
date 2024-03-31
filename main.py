import question_answer as ask
import streamlit as st

# Set The API Keys HERE
ask.setHuggingFaceApiKey("")
ask.setSerperApiKey("")

# Asker Object
asker_Search = ask.GetQuestionAnswer("search", modelIndex=1)
asker_Serper = ask.GetQuestionAnswer("serper", modelIndex=1)

st.title("Up-To-Date Question Answering")

question = st.text_input(label="Enter your Question",
                         placeholder="Your Question Here...", value="What is the Latest version of Node JS?")
col1, col2 = st.columns(2)

with col1:
    method = st.selectbox("Select Result Parse Method", [
        "Google Search", "Serper API"])

with col2:
    num_results = st.number_input(
        "Enter Search Numbers", min_value=2, max_value=12, value=5)

clicked = st.button("Get Answer")


if (clicked):
    if (method == "Google Search"):
        asker = asker_Search
    else:
        asker = asker_Serper

    asker.num_results = num_results
    with st.spinner("Searching for Question..."):
        asker.searchQuestion(question)

    with st.spinner("Parsing the Articles..."):
        asker.parseArticles()

    with st.spinner("Parsing final Answer..."):
        finalAnswer = asker.getFinalAnswer()

    if (not finalAnswer["success"]):
        st.error("Error Ocurred!")
        st.text("Error Data:\n", finalAnswer["result"])
    else:
        st.subheader("Your Answer:")
        st.text(finalAnswer["result"])

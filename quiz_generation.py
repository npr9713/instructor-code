import os
import json
import requests
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import FAISS
from groq import Groq

load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))



def get_pdf_text(pdf_file):
    text = ""
    pdf_reader = PdfReader(pdf_file)
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text



def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks



def generate_quiz_questions(context, difficulty, question_type, num_questions):
    difficulty_prompt = {
        "Easy": "Generate simple and straightforward questions that test basic knowledge. These questions should be designed for beginners and require minimal critical thinking, focusing on foundational concepts and definitions. Ideal for learners who are just starting to explore the topic.",

        "Medium": "Generate moderately challenging questions that require a deeper understanding of the subject matter. These questions should encourage learners to apply their knowledge and think critically, often involving problem-solving skills. Suitable for those who have some experience with the topic and are ready to tackle more complex ideas.",

        "Hard": "Generate complex and advanced questions that push the boundaries of the learner's knowledge and analytical abilities. These questions should require extensive understanding, synthesis of information, and the ability to make connections between different concepts. Designed for advanced learners who are well-versed in the topic and capable of tackling intricate problems."
    }

    question_type_prompt = {
        "MCQ": """
                Generate concise multiple-choice questions (MCQ) with exactly 4 answer options.
                Make sure that it is mcq so the answers and options should be striclty short and make sure that questions are like that as well. 
                Ensure the answer options are short and relevant. 
                Include the correct answer as part of the response.
                Also, provide a topic for each question.
                The response should be in valid and properly formatted JSON with indentation for readability.
                Dont add any other extra text other than the json response.(to be followed strictly).
                Each question should be represented as an object in an array with the following fields:
                - "question" (the MCQ question text)
                - "answer" (the correct answer)
                - "options" (an array containing the 4 answer options)
                - "topic" (the topic of the question).
                """,
        "Fill in the Blanks": """
                Generate concise fill-in-the-blank questions. 
                Ensure the blanks are meaningful and avoid overly long statements. 
                Provide the correct answer for each blank.
                Also, provide a topic for each question.
                The response should be in valid and properly formatted JSON with indentation for readability.
                Dont add any other text other than the json response.(to be followed strictly).
                Each question should be represented as an object in an array with the following fields:
                - "question" (the fill-in-the-blank question text, with the blank represented by '____')
                - "answer" (the correct word/phrase that fills the blank)
                - "topic" (the topic of the question).
                """
    }

    query = f"Context: {context}\n\nGenerate {num_questions} {question_type} questions based on this context. {difficulty_prompt[difficulty]} {question_type_prompt[question_type]}"

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": query,
            }
        ],
        model="llama3-8b-8192",
    )

    return chat_completion.choices[0].message.content



def create_vector_store(chunks):
    embeddings = SentenceTransformerEmbeddings(model_name="paraphrase-MiniLM-L6-v2")
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store

def fetch_relevant_documents(query, vector_store, num_chunks=3):
    docs = vector_store.similarity_search(query, k=num_chunks)
    return " ".join([doc.page_content for doc in docs])



def fetch_groups():
    token = st.session_state.get('token')
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    response = requests.post("http://localhost:3540/find_groups", headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'groups' in data:
            return data['groups']
        else:
            st.error("Invalid response structure.")
    else:
        st.error("Failed to fetch groups.")
    return []


def assign_tests(token, group_name, questions):
    payload = {
        "group": group_name,
        "questions": questions
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post("http://localhost:3540/assign_tests", json=payload, headers=headers)
    return response.status_code == 200, response.text


def quiz_generation_app():
    st.title("AI-Powered Quiz Generation")

    groups = fetch_groups()


    selected_group = st.selectbox("Select Group", groups)


    uploaded_file = st.file_uploader("Upload learning material (PDF)", type=["pdf"])
    if uploaded_file is not None:
        pdf_text = get_pdf_text(uploaded_file)
        if pdf_text:
            st.write("Learning material uploaded successfully.")

            query = st.text_input("Enter a query to fetch relevant content (optional)")


            text_chunks = get_text_chunks(pdf_text)
            vector_store = create_vector_store(text_chunks)

            difficulty = st.selectbox("Select quiz difficulty", ["Easy", "Medium", "Hard"])
            question_type = st.selectbox("Select question type", ["MCQ", "Fill in the Blanks"])
            num_questions = st.number_input("Number of questions", min_value=1, step=1)

            if st.button("Generate Quiz"):
                st.write("Generating quiz...")


                if query:
                    context = fetch_relevant_documents(query, vector_store)
                else:
                    context = " ".join(text_chunks[:3])

                response = generate_quiz_questions(context, difficulty, question_type, num_questions)

                start_index = response.find('[')


                end_index = response.rfind(']')


                json_string = response[start_index:end_index + 1]


                questions = json.loads(json_string)
                st.write(questions)

                if st.button("Assign Quiz"):
                    token = st.session_state.get('token')  # Assuming 'token' is stored in session state
                    success, message = assign_tests(token, selected_group, questions)

                    if success:
                        # If the response message includes the inserted questions
                        if isinstance(message, dict) and 'questions' in message:
                            st.success("Quiz assigned successfully!")
                            st.write("Inserted Questions")
                        else:
                            st.error("Unexpected response structure.")
                    else:
                        st.error(f"Failed to assign quiz: {message}")

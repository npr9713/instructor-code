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
from pinecone import Pinecone, ServerlessSpec
import pinecone
import uuid
import base64


load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pdf_vectors_index = pinecone.Index("pdf_vectors", host=os.getenv("PINECONE_INDEX_HOST"))


user_id_val = []
def generate_unique_document_id():
    return str(uuid.uuid4())



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
    return vector_store, chunks, embeddings

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
        user_id = data.get('mailId', None)
        groups = data.get('groups', [])
        if user_id:
            return user_id, groups
    else:
        st.error("Failed to fetch groups.")
    return None, []


def assign_tests(token, group_name, questions,quiz_name,is_retest_needed,max_retests,min_marks_for_retest,total_marks,marks_for_each_qn,vector_store,texts,user_id,document_id,embeddings,pdf_binary):
    pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
    payload = {
        "group": group_name,
        "questions": questions,
        "quiz_name":quiz_name,
        "is_retest_automated":is_retest_needed,
        "max_retests_allowed":max_retests,
        "min_marks_for_retest":min_marks_for_retest,
        "total_marks":total_marks,
        "marks_for_each_qn":marks_for_each_qn,
        "pdf_binary":pdf_base64,
        "document_id":document_id,
    }
    print("payload: ",payload)
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post("http://localhost:3540/assign_tests", json=payload, headers=headers)
    return response.status_code == 200, response.text


def quiz_generation_app():
    st.title("AI-Powered Quiz Generation")

    # Ensure session state variables are initialized
    if 'questions' not in st.session_state:
        st.session_state['questions'] = None
    if 'quiz_generated' not in st.session_state:
        st.session_state['quiz_generated'] = False
    if 'total_marks' not in st.session_state:
        st.session_state['total_marks'] = 0


    if 'groups' not in st.session_state or 'user_id' not in st.session_state:
        user_id, groups = fetch_groups()
        if user_id and groups:
            st.session_state['user_id'] = user_id
            st.session_state['groups'] = groups
        else:
            st.error("Failed to retrieve user ID and groups.")
            return

    selected_group = st.selectbox("Select Group", st.session_state['groups'])
    quiz_name = st.text_input("Quiz Name")

    is_retest_needed = st.checkbox("Is automated retest needed?")
    marks_for_each_qn = st.number_input("Marks for each question", min_value=1, step=1)
    min_marks_for_retest = 0
    max_retests = 0;

    if is_retest_needed:
        max_retests = st.number_input("Max Retests Allowed", min_value=1, step=1)

    uploaded_file = st.file_uploader("Upload learning material (PDF)", type=["pdf"])
    if uploaded_file is not None:
        pdf_binary = uploaded_file.read()
        pdf_text = get_pdf_text(uploaded_file)
        if pdf_text:
            st.write("Learning material uploaded successfully.")


            query = st.text_input("Enter a query to fetch relevant content (optional)")


            text_chunks = get_text_chunks(pdf_text)
            vector_store, texts,embeddings = create_vector_store(text_chunks)


            difficulty = st.selectbox("Select quiz difficulty", ["Easy", "Medium", "Hard"])
            question_type = st.selectbox("Select question type", ["MCQ", "Fill in the Blanks"])
            num_questions = st.number_input("Number of questions", min_value=1, step=1)

            if st.button("Generate Quiz"):
                st.write("Generating quiz...")


                context = fetch_relevant_documents(query, vector_store) if query else " ".join(text_chunks[:3])


                response = generate_quiz_questions(context, difficulty, question_type, num_questions)


                start_index = response.find('[')
                end_index = response.rfind(']')
                json_string = response[start_index:end_index + 1]


                st.session_state['questions'] = json.loads(json_string)
                st.session_state['quiz_generated'] = True


                st.session_state['total_marks'] = marks_for_each_qn * len(st.session_state['questions'])
                st.write(st.session_state['questions'])
                st.write(f"Total Marks: {st.session_state['total_marks']}")

                if is_retest_needed:
                    min_marks_for_retest = st.number_input("Minimum marks required for retest", min_value=1,
                                                           max_value=st.session_state['total_marks'])
                else:
                    min_marks_for_retest = 0


            if st.session_state['quiz_generated']:
                if st.button("Assign Quiz"):
                    st.write("Assign Quiz button clicked.")
                    token = st.session_state.get('token')
                    document_id = generate_unique_document_id()
                    user_id = st.session_state['user_id']

                    if not token:
                        st.error("Authorization token is missing.")
                        return


                    success, message = assign_tests(
                        token,
                        selected_group,
                        st.session_state['questions'],
                        quiz_name,
                        is_retest_needed,
                        max_retests,
                        min_marks_for_retest,
                        st.session_state['total_marks'],
                        marks_for_each_qn,
                        vector_store,
                        texts,
                        user_id,
                        document_id,
                        embeddings,
                        pdf_binary

                    )


                    if success:
                        if 'quiz_id' in message:
                            message_json = json.loads(message)
                            st.success("Quiz assigned successfully!")
                            st.write(f"Quiz ID: {message_json['quiz_id']}")
                        else:
                            st.error("Unexpected response structure.")
                    else:
                        st.error(f"Failed to assign quiz: {message}")

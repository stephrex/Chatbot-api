import os
import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_community.document_loaders import TextLoader
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain

load_dotenv()


class RAG():
    def __init__(self, text_file, dataset, path='./faq_db'):
        self.path = path
        self.text_file = text_file
        self.dataset = dataset
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        self.retriever = None
        self.vectorstore = None
        self.rag_chain = None

    def update_knowledge_base(self, about, products):
        with open(self.text_file, "w", encoding="utf-8") as f:
            f.write("## About the Business\n")
            f.write(about + "\n\n")

            f.write("## Frequently Asked Questions\n")
            for faq in self.dataset:  # Loop through the faqs. Changes based on the company's faqs structure format
                for question, answer in faq.items():
                    f.write(f"Q: {question}\nA: {answer}\n\n")

            f.write("## Product Listings\n")
            for product in products:
                f.write(
                    f"Book: {product['title']}\nPrice: {product['price']}\nAuthor: {product['author']}\n\n")

    def create_vector_store(self):
        # # Initialize Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')

        if not os.path.exists(self.text_file):
            print("Knowledge base file not found!")
            return

        loader = TextLoader(self.text_file)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=100
        )
        chunks = text_splitter.split_documents(documents)

        # Initialize ChromaDB and store vectors
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.vectorstore = Chroma.from_documents(
            chunks, embeddings, client=chroma_client)
        return self.vectorstore

    def retrieve_info(self, vectorstore):
        # Retrieve questions
        self.retriever = vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 5},
        )
        return self.retriever

    def query_LLM(self):
        contextualize_q_system_prompt = (
            "You are assisting with reformulating user questions within the context of a book-selling business. "
            "Your goal is to ensure that the user's query is interpreted correctly in relation to the company's services.\n\n"

            "**Instructions:**\n"
            "- If a user greets you (e.g., 'Hello', 'Hi'), reframe the question as a request for a request about the business.\n"
            "- If a user asks who you are, reframe it to clarify that you are an AI-powered assistant for the business.\n"
            "- If the user asks unrelated questions (e.g., about technology, general AI, or external topics), gently guide them back to book-related topics.\n"
            "- Keep all questions strictly within the scope of the business and its services."
        )

        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

        # This uses the LLM to help reformulate the question based on chat history
        history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, contextualize_q_prompt
        )

        qa_system_prompt = (
            "You are a **customer support assistant** for a business that sells books. "
            "Your primary role is to provide helpful, accurate information about the business, its products, and services. "
            "You should **only** answer questions related to the business and its offerings.\n\n"
            "You have access to product listings, including their prices and categories. "
            "When a user asks about a product, extract relevant product information from the provided context. "
            "If a user asks about a product’s price, availability, or description, answer directly using the given data. "
            "If the information is missing, say 'I couldn’t find the details, please check our website.' "

            "**Instructions:**\n"
            "- If the user greets (e.g., 'Hello', 'Hi', 'Good day'), respond with a friendly greeting introducing the business. Example: "
            "'Hello! Welcome to Book Next, your one-stop shop for books. How can I assist you today?'\n"
            "- If the user asks about the business (e.g., 'What do you do?', 'Tell me about your company'), provide details about the business and its products.\n"
            "- If the user asks who made you or who you are, reply as a customer support assistant for [Business Name]. Example: "
            "'I am an AI-powered customer support assistant for [Business Name], here to help you with book inquiries and purchases.'\n"
            "- If the user asks something unrelated (e.g., politics, weather, who is the president), politely redirect them back to the business context. Example: "
            "'I'm here to assist with book-related queries. How can I help you today?'\n\n"

            "Example Queries: "
            "- 'How much is the iPhone 15?' → 'The iPhone 15 costs $999.' "
            "- 'Do you have laptops?' → 'Yes, we have laptops including Dell, HP, and MacBooks.'"
            "**Important:** Always provide responses in a friendly and professional tone, staying within the business domain.\n\n"
            "{context}\n\n"
        )

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(
            self.llm, qa_prompt)

        self.rag_chain = create_retrieval_chain(
            history_aware_retriever, question_answer_chain)

        return self.rag_chain

    def continual_chat(self, prompt, chat_history):
        print("Start chatting with the AI!")
        # print(prompt)
        retrieved_docs = self.retriever.get_relevant_documents(prompt)

        # Debugging: Print the retrieved documents
        print("\n🔹 Retrieved Documents:")
        for i, doc in enumerate(retrieved_docs, 1):
            print(f"{i}. {doc.page_content} - Metadata: {doc.metadata}")

        formatted_chat_history = []
        for message in chat_history:
            if message["sender"] == "user":
                formatted_chat_history.append(
                    HumanMessage(content=message["text"]))
            elif message['sender'] == 'bot':
                formatted_chat_history.append(
                    AIMessage(content=message["text"]))

        # Process the user's query through the retrieval chain
        result = self.rag_chain.invoke(
            {"input": prompt,
             "chat_history": formatted_chat_history})

       # Update chat history
        chat_history.append({"text": prompt, "sender": "user"})
        # Store as JSON format for Firebase
        chat_history.append({"text": result["answer"], "sender": "bot"})

        return result['answer'], chat_history

    def run(self, prompt, chat_history):
        self.create_vector_store()
        self.retrieve_info(self.vectorstore)
        self.query_LLM()
        result, history = self.continual_chat(prompt, chat_history)
        return result, history

import os
import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from get_client_data import GetData
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

            # f.write("## Product Listings\n")
            # for product in products:
            #     f.write(
            #         f"Book: {product['title']}\nPrice: {product['price']}\nAuthor: {product['author']}\n\n")

            # f.write("\n## Product Listings/Phones/Electrical Appliances\n")
            # for product in products:
            #     product_line = (
            #         f"Product ID: {product.get('Product ID', 'N/A')} | "
            #         f"Name: {product.get('Product Name', 'N/A')} | "
            #         f"Category: {product.get('Category', 'N/A')} | "
            #         f"Brand: {product.get('Brand', 'N/A')} | "
            #         f"Model: {product.get('Model', 'N/A')} | "
            #         f"Description: {product.get('Description', 'N/A')} | "
            #         f"Specifications: {product.get('Specifications', 'N/A')} | "
            #         f"Price: {product.get('Price', 'N/A')} | "
            #         f"Stock: {product.get('Stock', 'N/A')} | "
            #         f"Warranty: {product.get('Warranty', 'N/A')}\n\n"
            #     )
            #     f.write(product_line)

            f.write("\n## Product Listings/Phones/Electrical Appliances\n\n")
            for product in products:
                product_line = (
                    f"Product ID: {product.get('Product ID', 'N/A')}\n"
                    f"Name: {product.get('Product Name', 'N/A')}\n"
                    f"Category: {product.get('Category', 'N/A')}\n"
                    f"Brand: {product.get('Brand', 'N/A')}\n"
                    f"Model: {product.get('Model', 'N/A')}\n"
                    f"Description: {product.get('Description', 'N/A')}\n"
                    f"Specifications: {product.get('Specifications', 'N/A')}\n"
                    f"Price: {product.get('Price', 'N/A')}\n"
                    f"Stock: {product.get('Stock', 'N/A')}\n"
                    f"Warranty: {product.get('Warranty', 'N/A')}\n\n"
                    f"---\n\n"
                )
                f.write(product_line)

    def create_vector_store(self):
        # # Initialize Embeddings
        print('[INFO] Creating Vectorstore in Persistent Dir')
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
            "You are assisting with reformulating user questions within the context of a electrical appliances store business. "
            "Your goal is to ensure that the user's query is interpreted correctly in relation to the company's services."
            "and that the right information regarding the users query is retireved from a database of the business\n\n"

            "**Instructions:**\n"
            "- If a user greets you (e.g., 'Hello', 'Hi'), reframe the question as a request for a request about the business.\n"
            "- If a user asks who you are, reframe it to clarify that you are an AI-powered assistant for the business.\n"
            "- If the user asks unrelated questions (e.g., about technology, general AI, or external topics), gently guide them back to electric store business-related topics.\n"
            "- Keep all questions strictly within the scope of the business and its services."
            "- always reformulate any question that is out of the scope of the business, or unrelated, to be guided back to the electric store business-related topics"
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
            "You are a customer support assistant for a business that sells electronics."
            "Your primary role is to provide helpful, accurate information about the business, its products, and services. You should only answer questions related to the business and its offerings."

            "You have access to live product listings, including their prices, specifications, and categories. When a user asks about a product, "
            "extract relevant product information from the provided context. "
            "If a user asks about a product’s price, availability, or description, answer directly using the given data. "
            "If the information is missing, tell them you couldn't find the details, and redirect them to the website or the human customer support, by giving them the contact details"
            "website: electronest.com, call/whatsapp: 07069117393, gmail: electronest@gmail.com"

            "Instructions:"
            'If the user greets (e.g., "Hello", "Hi", "Good day"), respond with a friendly greeting introducing the business. Example:'
            "Hello! Welcome to ElectroNest, your go-to store for the latest electronics. How can I assist you today?"
            'If the user asks about the business (e.g., "What do you do?", "Tell me about your company"), provide details about the store and its products.'
            'If the user asks who made you or who you are, reply as a customer support assistant for ElectroNest. Example:'
            "I am an AI-powered customer support assistant for ElectroNest, here to help you with electronics inquiries and purchases."
            'If the user asks something unrelated (e.g., politics, weather, who is the president, and sot of un-realted question that does not concern a customer support assistant), politely redirect them back to the business context. Example:'
            "I'm here to assist with electronics-related queries. How can I help you today?"
            'You would be given a list of products or faqs, when given product, if the amount in stock is mush just tell them we have a lot in stock, not the exact amount we have in stocks. If we have few you can tell them the amount we have in stock. Few can be anything less than 5'

            'Example Queries:'
            'How much is the iPhone 15?: The iPhone 15 costs $999.'
            "Do you have gaming laptops?: Yes, we have gaming laptops including Alienware, Razer, and ASUS ROG models."
            "What is the warranty on a Samsung TV?: The Samsung TV comes with a 1-year manufacturer warranty."
            "What can you say about today's weather: I am a customer support assistant, and I'm here to support you with your queries concerning ElectroNest"
            '1+1 is what: Sorry, I cant give you information about that, i am customer support assisitant for ElectroNest'

            'Important:'
            'Always provide responses in a friendly and professional tone, staying within the electronics business domain.'
            'Never Never Never Never answer any unrelated questions that doesnt concern the business and a customer support assistant'
            'You are limited to the companys information alone'
            'Act like a customer support assistant, with so much marketing skills, parsuade the customer by all means to buy your product'
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
        self.retrieve_info(self.vectorstore)
        self.query_LLM()
        result, history = self.continual_chat(prompt, chat_history)
        return result, history

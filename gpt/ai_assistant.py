from openai import OpenAI
from werkzeug.datastructures import FileStorage

from configs.config import OPEN_AI_API_KEY, ASSISTANT_ID, VECTOR_STORE_ID

API_KEY = OPEN_AI_API_KEY
client = OpenAI(api_key=API_KEY)

instruction = """
You are an assistant designed to serve as an Inquiry Support assistant for O'zbekiston Respublikasi Adliya Vazirligi, a government organization. Your role is to address user inquiries accurately and provide authoritative information based solely on the knowledge base.

Language:
Use only Uzbek language. If users ask you questions in other languages, say "Ushbu bot davlat tilida yuritiladi. Zaruriyatga qarab kelgusida boshqa tillarda ham yuritilishi mumkin.". If users ask you questions in Uzbek language and you do not have information about the question being asked, tell them in Uzbek language that you do not have information about them saying "Kechirasiz, men hozirda sizning so'rovinggiz to'g'risida ma'lumotga ega emasman." for instance.

Context
Adliya Vazirligi is a government body responsible for overseeing legal and administrative matters. You act as a primary point of contact for the public, providing information about services, procedures, and legal regulations. Users may ask about legal decrees, processes, or specific policies, and you are expected to deliver precise and detailed responses.

User Input:
Users may input their phone number, passport series, and credit card numbers. They are given to you as MASK_PHONE, MASK_PASSPORT, and MASK_CARD_NUMBER. Feel free to generate a response by adding placeholders into your response. While retrieving, masked placeholders are changed with real values. You do not have to warn users about not sending their personal info, they also masked! Do not tell users not to send their personal data it is totally fine, just use placeholders while generating a response!!!


Examples:
User Inquiry:
“2020-yilgi qarorga oid ma'lumotlarni bera olasizmi?”

Your Response:
“2020-yil 10-yanvardagi 18-son qaroriga muvofiq, ushbu qaror davlat xizmatlarining elektron shaklga o‘tish bosqichlarini belgilaydi. Batafsil ma’lumot uchun qarorning asosiy bo‘limlariga murojaat qilishingiz mumkin.”

Persona
Role: Adliya Vazirligi Yordamchi Boti.

Characteristics: Authoritative, professional, and highly knowledgeable about Adliya Vazirligi’s legal framework, policies, and services.

Behavior:
Provide concise and accurate responses.
Avoid unnecessary elaboration.
Rely strictly on the knowledge base for information.
Do not answer any other questions out of the scope. Users may ask questions about math, science, in short, about anything. Your task is to answer only questions about Adliya based on the knowledge files your are given!!!
Communicate in a manner that reflects the organization's formality and professionalism.

Format:
Respond in plain text without any special formatting (e.g., no bold, italic, or hyperlinks).
Include precise legal citations (e.g., 2020-yil 10-yanvardagi 18-son qarori) when applicable.
Provide detailed yet succinct explanations about Adliya Vazirligi’s services and processes.
Do not reference external links or include information outside the scope of the knowledge base.

Tone:
Formal and professional.
Friendly and respectful, ensuring accessibility for all users while maintaining the authoritative voice of a government organization.
This version shifts the focus to your role as the assistant while maintaining a structured and professional tone.

NOW IT'S TIME TO ANSWER THE QUESTIONS STRICTLY BASED ON THE KNOWLEDGE BASE. IF INFORMATION/ANSWER TO THE QUESTIONS EXISTS IN THE KNOWLEDGE BASE, PROVIDE IT. OTERWISE, ACT AS INSTRUCTED.
"""


# create vector store
def create_vector_store(name: str):
    v_store = client.beta.vector_stores.create(name=name)
    print(f"Vector Store ID: {v_store.id}\n")
    return v_store


# upload file(s)
def upload_files(vector_store_id: str, *file_paths):
    file_streams = [open(path, "rb") for path in file_paths]
    print(f"File Streams: {file_streams}\n")

    # attach the file(s) to the vector store
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id,
        files=file_streams
    )
    print(f"File Batch: {file_batch}\n")

    # check the status of the attached files
    while file_batch.status != "completed":
        print(f"File Batch Status: {file_batch.status}")
    print(f"File Batch Status: {file_batch.status}\n")


# upload file
def upload_file_to_vector_store(file_storage: FileStorage):
    # attach the file(s) to the vector store
    file_streams = [(file_storage.filename, file_storage, file_storage.content_type)]
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=VECTOR_STORE_ID,
        files=file_streams
    )
    print(f"File Batch: {file_batch}\n")


# create assistant
def create_assistant(name: str, vector_store_id: str):
    assistant = client.beta.assistants.create(
        name=name,
        model="gpt-4o-mini",
        instructions=instruction,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
    )
    print(f"Assistant created: {assistant}")
    return assistant


def update_assistant_name(name: str):
    assistant = client.beta.assistants.update(
        assistant_id="asst_h4ho8baFaXAYHJTAyirtmPPC",
        name=name
    )
    print(f"Assistant name updated: {assistant}")


async def create_thread():
    new_thread = client.beta.threads.create()
    print(f"Thread created: {new_thread}")
    return new_thread.id


async def send_message(text: str, thread_id):
    try:
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)
        run = client.beta.threads.runs.create_and_poll(thread_id=thread_id, assistant_id=ASSISTANT_ID)
        messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))
        assistant_response = messages[0].content[0].text.value

        print(f"User: {text}")
        print(f"Assistant: {assistant_response}")
        print(f"Messages: {messages}")

        return {'assistant_response': assistant_response, 'assistant_message_id': messages[0].id}
    except Exception as e:
        print(f'Error occurred while getting message from OpenAI: {e}')
        return {
            'assistant_response': 'Kechirasiz, texnik nosozlik yuz berdi! Iltimos, keyinroq urinib ko\'ring.',
            'assistant_message_id': None
        }


def list_all_messages_by_thread_id(thread_id: str):
    messages = list(client.beta.threads.messages.list(thread_id=thread_id, order="asc"))
    conversations = {}
    print(f"Messages: {messages}")
    i = 0
    while i < len(messages):
        message = messages[i]
        if message.role == 'user':
            print(f"User: {message.content[0].text.value}")
            if "user" not in conversations:   # check if the list 'user' is emtpy
                conversations["user"] = [message.content[0].text.value]
                print(f"User's messages have been initiated: {conversations['user']}")
            else:
                conversations["user"].append(message.content[0].text.value)
                print(f"User message has been added: {conversations['user']}")
        elif message.role == 'assistant':
            print(f"Assistant: {message.content[0].text.value}")
            if "assistant" not in conversations:
                conversations["assistant"] = [message.content[0].text.value]
                print(f"Assistant's messages have been initiated: {conversations['assistant']}")
            else:
                conversations["assistant"].append(message.content[0].text.value)
                print(f"Assistant message has been added: {conversations['assistant']}")
        i += 1
        print("\n")

    return conversations


# vector_store = create_vector_store("vector_store")
# upload_files(
#     vector_store.id,
#     "C:/Users/Ulugbek/Desktop/MyWorks/Books/Java_the_Complete_Reference_11th_Ed.pdf",
#     "C:/Users/Ulugbek/Desktop/MyWorks/Books/Python Crash Course.pdf",
#     "C:/Users/Ulugbek/Desktop/MyWorks/Books/Algorithms 3rd Ed.pdf",
#     "C:/Users/Ulugbek/Desktop/MyWorks/Books/Algorithms 4th Ed.pdf"
# )
# create_assistant(name="Software Bot", vector_store_id=vector_store.id)
# update_assistant_name("Software Assistant")
# send_message("What is memoization?", create_thread())
# send_message(
#     "Can you show me an example of solving the Fibonacci sequence with memoization?",
#     "thread_4WaWuzPul3rtAD2oPcDFp4iI"
# )
# list_all_messages_by_thread_id("thread_4WaWuzPul3rtAD2oPcDFp4iI")

import time

import asyncio

from aiogram import types, Bot
from httpx import RemoteProtocolError
from openai import OpenAI
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent, ResponseTextDoneEvent

from configs.config import OPEN_AI_API_KEY, ASSISTANT_ID, VECTOR_STORE_ID

API_KEY = OPEN_AI_API_KEY
client = OpenAI(api_key=API_KEY)
async_client = AsyncOpenAI(api_key=API_KEY)

instruction = """
You are an assistant designed to serve as an Inquiry Support assistant for O'zbekiston Respublikasi Adliya Vazirligi, a government organization. Your role is to address user inquiries accurately and provide authoritative information based solely on the knowledge base.

Language:
Use only Uzbek language. Users ask you questions only in Uzbek language. However, questions still may contain the words like 'MASK_PHONE', 'MASK_PASSPORT', and 'MASK_CARD_NUMBER', which you must treat as real parameters in Uzbek language. If users ask you questions in other languages, say "Ushbu bot davlat tilida yuritiladi. Zaruriyatga qarab kelgusida boshqa tillarda ham yuritilishi mumkin.". If users ask you questions in Uzbek language and you do not have information about the question being asked, tell them in Uzbek language that you do not have information about them saying "Kechirasiz, men hozirda sizning so'rovinggiz to'g'risida ma'lumotga ega emasman." for instance.

Context
Adliya Vazirligi is a government body responsible for overseeing legal and administrative matters. You act as a primary point of contact for the public, providing information about services, procedures, and legal regulations. Users ask you about legal decrees, processes, or specific policies, and you are expected to deliver precise and detailed responses. Users may also ask about who you are or what you can do, where you should provide information about yourself too, like who you are, and what you can do.

User Input:
Users may input their phone number, passport series, and credit card numbers. They are given to you as MASK_PHONE, MASK_PASSPORT, and MASK_CARD_NUMBER. Feel free to generate a response by adding placeholders into your response. While retrieving, masked placeholders are changed with real values. You do not have to warn users about not sending their personal info, they are also masked! Do not tell users not to send their personal data, it is totally fine, just use placeholders while generating a response!!!


Examples:
Sample User Inquiry 1:
    “2020-yilgi qarorga oid ma'lumotlarni bera olasizmi?”

Your Response 1:
    “2020-yil 10-yanvardagi 18-son qaroriga muvofiq, ushbu qaror davlat xizmatlarining elektron shaklga o‘tish bosqichlarini belgilaydi. Batafsil ma’lumot uchun qarorning asosiy bo‘limlariga murojaat qilishingiz mumkin.”

Persona
Role: Adliya Vazirligi Yordamchi Boti.

Sample User Inquiry 2:
    “Men plastik kartamni yo'qotib qo'ydim, uning karta raqami MASK_CARD_NUMBER edi. Kartamni qanday qilib topsam bo'ladi?”

Your Response 2:
    “Agarda siz shaxsiy plastik kartanggizni yo'qotib qo'ygan bo'lsanggiz, kartani topish yoki qayta tiklash uchun quyidagi amallarni bajarishingiz mumkin:
        Bank bilan bog'laning - Ular sizga kartangizni bloklash va yangi kartani chiqarish bo'yicha yordam bera olishadi.
        Mobil bank ilovasi yoki internet banking orqali yangi karta buyurtma qiling - Bank yangi kartani chiqarishga yordam beradi. U yangi karta raqami va PIN bilan birga sizga yetkazib beriladi. 
        Plastik kartanggizni yo'qotib qo'yganinggiz haqida yaqinlaringgizga ma'lum qiling - Yaqinlaringgiz sizga kartanggizni topishga yordam bera olishlari mumkin. 
    
    Kartanggiz yo'qolgan holatda, u bilan nomaqbul ishlashlar yuz berishining oldini olish uchun plastik kartanggizni bloklashinggiz tavsiya etiladi.”

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
    v_store = client.vector_stores.create(name=name)
    print(f"Vector Store ID: {v_store.id}\n")
    return v_store


# upload file(s)
def upload_files(vector_store_id: str, *file_paths):
    file_streams = [open(path, "rb") for path in file_paths]
    print(f"File Streams: {file_streams}\n")

    # attach the file(s) to the vector store
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id,
        files=file_streams
    )
    print(f"File Batch: {file_batch}\n")

    # check the status of the attached files
    while file_batch.status != "completed":
        print(f"File Batch Status: {file_batch.status}")
    print(f"File Batch Status: {file_batch.status}\n")


# upload file
def upload_file_to_openai(filename: str):
    try:
        response = client.files.create(
            file=open(filename, "rb"),
            purpose="assistants"
        )
        print(f"Uploaded file response: {response}")
        return response.id
    except Exception as e:
        print(f"Error while uploading file: {e}")
        return None


# upload file to vector store
def upload_file_to_vector_store(file_id: str):
    try:
        # Attach the file to the vector store
        file_batch = client.vector_stores.files.create_and_poll(
            vector_store_id=VECTOR_STORE_ID,
            file_id=file_id
        )
        print(f"File Batch: {file_batch}")
        return file_batch.id
    except Exception as e:
        print(f"Error while uploading file: {e}")
        return None


# delete file
def delete_file_from_vector_store(file_id: str):
    try:
        # Detach a file by the file_id from the vector store
        delete_response = client.vector_stores.files.delete(
            vector_store_id=VECTOR_STORE_ID,
            file_id=file_id
        )
        print(f"Delete response: {delete_response}")
    except Exception as e:
        print(f"Error while deleting file from vector store: {e}")
        raise e


def delete_file_from_openai(file_id: str):
    try:
        deletion_status = client.files.delete(file_id=file_id)
        print(f"Deletion status: {deletion_status}")
    except Exception as e:
        print(f"Error while deleting file from OpenAI: {e}")
        raise e


async def stream_response(text: str, message: types.Message, bot: Bot):
    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            start = time.time()
            print("===============================================")
            stream = client.responses.create(
                model="gpt-4o-mini",
                input=text,
                stream=True,
            )
            response = ''
            i = 0
            asst_response = await bot.send_message(chat_id=message.chat.id, text=text[0])
            for event in stream:
                if isinstance(event, ResponseTextDeltaEvent):
                    response += event.delta
                elif isinstance(event, ResponseTextDoneEvent):
                    pass
                print(event)
                i = i + 1
                if response != '' and response != text[0] and i%5 == 0:
                    await bot.edit_message_text(chat_id=message.chat.id, message_id=asst_response.message_id, text=response)

            print("===============================================")
            end = time.time()
            print(f"Time spent for stream response: {(end - start)} seconds")
            print("Final Response:", response)
            return response  # Success, return the response

        except RemoteProtocolError as e:
            print(f"Error: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
            attempt += 1
            time.sleep(2)  # Wait before retrying (you can adjust the delay)

    raise Exception("Max retries reached. Could not complete the request.")


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


async def send_message_to_open_ai(text: str, thread_id: str, run_id: str = 'no_run_for_first_ever_message'):
    try:
        start = time.time()
        # Add message to thread
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

        # Run the assistant with the above thread, which has user message in it
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

        # Wait for completion
        while run.status != "completed":
            # Be nice to the API
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))
        assistant_response = messages[0].content[0].text.value

        end = time.time()

        print(f"User: {text}")
        print(f"Assistant: {assistant_response}")
        print(f"Messages: {messages}")
        print(f"Time spent for OpenAI: {(end - start)} seconds")

        return {
            'assistant_response': assistant_response,
            'assistant_message_id': messages[0].id,
            'assistant_run_id': run.id
        }
    except Exception as e:
        print(f'Error occurred while getting message from OpenAI: {e}')
        if e.__str__().__contains__('already has an active run') or e.__str__().__contains__("Can't add messages to thread_"):
            try:
                last_run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

                # Cancel the active run
                print(f"Cancelling run: {run_id}")
                while last_run.status != "cancelled":
                    last_run = client.beta.threads.runs.cancel(
                        thread_id=thread_id,
                        run_id=run_id
                    )
                print(f"Cancelled run {last_run} successfully")

                # Add message to thread
                client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

                # Run the assistant with the above thread, which has user message in it
                run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

                # Wait for completion
                while run.status != "completed":
                    # Be nice to the API
                    time.sleep(0.5)
                    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

                messages = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))
                assistant_response = messages[0].content[0].text.value

                print(f"User: {text}")
                print(f"Assistant: {assistant_response}")
                print(f"Messages: {messages}")

                return {
                    'assistant_response': assistant_response,
                    'assistant_message_id': messages[0].id,
                    'assistant_run_id': run.id
                }
            except Exception as e:
                print(f'Error occurred while cancelling run and re-sending prompt to OpenAI: {e}')
        return {
            'assistant_response': "Kechirasiz, texnik nosozlik yuz berdi! Iltimos, keyinroq urinib ko'ring.",
            'assistant_message_id': None,
            'assistant_run_id': None
        }


async def send_async_message_to_open_ai(text: str, thread_id: str, run_id: str = 'no_run_for_first_ever_message'):
    try:
        start = time.time()
        # Add message to thread
        await async_client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

        # Run the assistant with the above thread, which has user message in it
        run = await async_client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

        # Wait for completion
        while run.status != "completed":
            # Be nice to the API
            # time.sleep(0.5)
            await asyncio.sleep(0.5)
            run = await async_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        messages_list = await async_client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id)
        messages = messages_list.data
        assistant_response = messages[0].content[0].text.value

        end = time.time()

        print(f"User: {text}")
        print(f"Assistant: {assistant_response}")
        print(f"Messages: {messages}")
        print(f"Time spent for OpenAI: {(end - start)} seconds")

        return {
            'assistant_response': assistant_response,
            'assistant_message_id': messages[0].id,
            'assistant_run_id': run.id
        }
    except Exception as e:
        print(f'Error occurred while getting message from OpenAI: {e}')
        if e.__str__().__contains__('already has an active run') or e.__str__().__contains__("Can't add messages to thread_"):
            try:
                last_run = await async_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

                # Cancel the active run
                print(f"Cancelling run: {run_id}")
                while last_run.status != "cancelled":
                    last_run = await async_client.beta.threads.runs.cancel(
                        thread_id=thread_id,
                        run_id=run_id
                    )
                print(f"Cancelled run {last_run} successfully")

                # Add message to thread
                await async_client.beta.threads.messages.create(thread_id=thread_id, role="user", content=text)

                # Run the assistant with the above thread, which has user message in it
                run = await async_client.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

                # Wait for completion
                while run.status != "completed":
                    # Be nice to the API
                    await asyncio.sleep(0.5)
                    run = await async_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

                messages_list = await async_client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id)
                messages = messages_list.data
                assistant_response = messages[0].content[0].text.value

                print(f"User: {text}")
                print(f"Assistant: {assistant_response}")
                print(f"Messages: {messages}")

                return {
                    'assistant_response': assistant_response,
                    'assistant_message_id': messages[0].id,
                    'assistant_run_id': run.id
                }
            except Exception as e:
                print(f'Error occurred while cancelling run and re-sending prompt to OpenAI: {e}')
        return {
            'assistant_response': "Kechirasiz, texnik nosozlik yuz berdi! Iltimos, yana bir urinib ko'ring.",
            'assistant_message_id': None,
            'assistant_run_id': None
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

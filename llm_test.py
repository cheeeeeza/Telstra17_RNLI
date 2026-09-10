import requests
import paramiko
import getpass
import base64

haku_ip = "10.234.6.18"
haku_user = "nao"

password = getpass.getpass("Haku password: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(haku_ip, username=haku_user, password=password)


def get_llm_reply(message):
    data = {
        "model": "llama3.2:3b",
        "prompt": message,
        "stream": False
    }

    response = requests.post(
        "http://localhost:11434/api/generate",
        json=data
    )

    return response.json()["response"]


def haku_speak(message):
    encoded = base64.b64encode(message.encode("utf-8")).decode("utf-8")

    command = (
        "python -c \"import base64; "
        "from naoqi import ALProxy; "
        "tts=ALProxy('ALTextToSpeech','127.0.0.1',9559); "
        "tts.say(base64.b64decode('" + encoded + "'))\""
    )

    ssh.exec_command(command)


print("Haku LLM Test")
print("Type exit to stop")

while True:
    message = input("\nYou: ")

    if message.lower() == "exit":
        break

    if message.strip() == "":
        print("Please enter a message")
        continue

    reply = get_llm_reply(message)

    print("Haku:", reply)
    haku_speak(reply)

ssh.close()
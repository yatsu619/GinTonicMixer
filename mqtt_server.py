import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Verbunden mit Code:", rc)
    client.subscribe("cocktail/#")  # alle relevanten ESP-Topics

def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883)
client.loop_forever()
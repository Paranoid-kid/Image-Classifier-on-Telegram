import socket
import logging.config
import numpy as np
import threading
import json
import base64
import tensorflow as tf
from queue import Queue
from keras.applications.resnet50 import ResNet50
from keras.preprocessing import image
from keras.applications.resnet50 import preprocess_input, decode_predictions

global graph, model
graph = tf.get_default_graph()
model = ResNet50(weights='imagenet')
logging.config.fileConfig('logconfig.ini')


def predict(image_name):
    logging.info('Image Received by Model')
    img = image.load_img(image_name, target_size=(224, 224))
    x = preprocess_input(np.expand_dims(image.img_to_array(img), axis=0))

    with graph.as_default():
        preds = model.predict(x)
    pred_items = decode_predictions(preds, top=5)[0]
    predictions = []
    for pred_item in pred_items:
        _, label, proba = pred_item
        prediction = {"label": label, "proba": float(proba)}
        predictions.append(prediction)
    return predictions


# parse the data
def load_data(soc):
    header = soc.recv(8).decode('utf-8')
    if '\n' not in header:
        logging.error('saw no newline in the first 8 bytes')
    else:
        len_str, json_str = header.split('\n', 1)
        to_read = int(len_str) - len(json_str)
        if to_read > 0:
            json_str += soc.recv(to_read, socket.MSG_WAITALL).decode('utf-8')
        return json_str


#  Main Thread: Listening for incoming connections from clients
def serve(addr, out_q):
    logging.info('Server Starting !')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(addr)
    server_socket.listen(10)
    while True:
        client_socket, client_address = server_socket.accept()
        client_socket.settimeout(10.0)
        out_q.put((client_socket, client_address))
        # logging.debug('thread %s is running...' % threading.current_thread().name)


#  Thread 2
def recv_send_img(in_q):
    while True:
        client_socket, client_address = in_q.get()
        logging.info('----------Got Connection From {}-------'.format(client_address))
        # logging.debug('thread %s is running...' % threading.current_thread().name)
        json_data = json.loads(load_data(client_socket))
        image_data = base64.b64decode(json_data['image'])
        chat_id = json_data['chat_id']
        image_name = json_data['image_name']
        with open(image_name, 'wb') as f:
            f.write(image_data)
        predictions = predict(image_name)
        json_response = {
            'predictions': predictions,
            'chat_id': chat_id
        }
        json_str = json.dumps(json_response)
        wrapped_msg = '{}\n{}'.format(len(json_str), json_str)
        client_socket.send(wrapped_msg.encode('utf-8'))
        logging.info('Response has been sent back to bot.py [chat_id] is [{}]'.format(chat_id))
        client_socket.shutdown(socket.SHUT_WR)
        logging.info('----------Closed connection from {}----------'.format(client_address))


if __name__ == '__main__':
    q = Queue()
    t1 = threading.Thread(target=serve, args=(('', 20000), q,), name='Main Thread')
    t2 = threading.Thread(target=recv_send_img, args=(q,), name='Thread 2')
    t1.start()
    t2.start()

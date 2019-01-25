import time
import random
import telepot
from telepot.loop import MessageLoop
import logging
import logging.config
import base64
import json
import requests
from queue import Queue
import socket
import threading
import os

logging.config.fileConfig('logconfig.ini')
IMG_PATH = 'pic/'


def load_data(soc):
    header = soc.recv(6).decode('utf-8')
    if '\n' not in header:
        logging.error('saw no newline in the first 6 bytes')
    len_str, json_str = header.split('\n', 1)
    to_read = int(len_str) - len(json_str)
    if to_read > 0:
        json_str += soc.recv(to_read, socket.MSG_WAITALL).decode('utf-8')
    return json_str


def get_filename(chat_id):
    time_stamp = time.strftime('%Y%m%d%H%M%S') + str(random.randint(1, 100))
    return str(chat_id) + '_' + time_stamp + '.png'


def serialize(file_path, chat_id, image_name):
    with open(file_path, "rb") as image_file:
        encoded_img = base64.b64encode(image_file.read())
    json_str = {
        'image': encoded_img.decode('utf-8'),
        'chat_id': chat_id,
        'image_name': image_name
    }
    json_str = json.dumps(json_str)
    wrapped_msg = '{}\n{}'.format(len(json_str), json_str)
    return wrapped_msg


def download_img_thro_url(url, img_name, chat_id):
    response = requests.get(url)
    logging.info('The Response Status: {}'.format(response.status_code))
    if response.status_code == 200 and response.headers.get('content-type').split('/')[0] == 'image':
        img = response.content
        with open(IMG_PATH + img_name, 'wb') as f:
            f.write(img)
        logging.info('Image downloaded in: {}{}'.format(IMG_PATH, img_name))
    else:
        logging.error('The Response status: {}'.format(response.status_code))
        logging.error('The Response content-type is: {}'.format(response.headers.get('content-type')))
        error_msg = 'The URL you sent does not point to an image! Please try another one.'
        bot.sendMessage(chat_id, error_msg)


#  Thread 1 ­ Receiving Messages
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    logging.info('----------Got Connection From User [{}]-------'.format(chat_id))
    file_name = get_filename(str(chat_id))
    img_path = IMG_PATH + file_name
    logging.debug('content_type is: {}'.format(content_type))
    logging.debug('chat_id is: {}'.format(chat_id))

    if content_type == 'text':
        image_url = msg['text']
        if image_url.startswith('http://') or image_url.startswith('https://'):
            logging.info('----------Download Image Through URL----------')
            logging.debug('Image URL is: {}'.format(image_url))
            download_img_thro_url(image_url, file_name, chat_id)
            if os.path.exists(img_path):
                wrapped_msg = serialize(img_path, chat_id, file_name)
                queue_1.put(wrapped_msg)
                # logging.debug('Queue 1 has been put')

    if content_type == 'photo':
        logging.info('----------Download Image From Telegram----------')
        bot.download_file(msg['photo'][-1]['file_id'], img_path)
        wrapped_msg = serialize(img_path, chat_id, file_name)
        queue_1.put(wrapped_msg)
        # logging.debug('Queue 1 has been put')


#  Thread 2 ­ Client Thread
def send_recv_img(in_queue_1, out_queue_2):
    while True:
        # logging.debug('thread %s is running...' % threading.current_thread().name)
        wrapped_msg = in_queue_1.get()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 20000))
        logging.info('The connection to the Server has been established')
        client_socket.sendall(wrapped_msg.encode('utf-8'))
        logging.info('Image has been sent to Server')
        # receive the response from server and put it into queue_2
        out_queue_2.put(load_data(client_socket))
        logging.info('Prediction result from the server has been received')
        # logging.debug('Queue 2 has been put')


# Thread 3 ­ Sending Messages
def send_response(in_queue_2):
    while True:
        # logging.debug('thread %s is running...' % threading.current_thread().name)
        json_response_rec = in_queue_2.get()
        json_response = json.loads(json_response_rec)
        chat_id = json_response['chat_id']
        prediction_list = list(json_response['predictions'])
        result = ''
        for index, prediction in enumerate(prediction_list):
            label = prediction['label']
            proba = prediction['proba']
            result += '{}. {} ({:.4f})\n'.format(index + 1, label, proba)
        bot.sendMessage(chat_id, result)
        logging.info('Predction result has been sent back to the User [{}].'.format(chat_id))
        logging.info('----------END----------')


if __name__ == "__main__":
    bot = telepot.Bot('')
    queue_1 = Queue()
    queue_2 = Queue()
    MessageLoop(bot, handle).run_as_thread()
    # logging.debug('thread %s is running...' % threading.current_thread().name)
    t2 = threading.Thread(target=send_recv_img, args=(queue_1, queue_2,), name='Thread 2')
    t3 = threading.Thread(target=send_response, args=(queue_2,), name='Thread 3')
    t2.start()
    t3.start()

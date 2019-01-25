# Image Classifier on Telegram

Practice socket programming and multi-threaded programming in Python.

## Model

> [Keras pre-trained ResNet50 model](https://keras.io/applications/#resnet50)

## System Architecture

![image-20181222205752643](http://github.com/Paranoid-kid/Image-Classifier-on-Telegram/raw/master/img/1.png)

The system offer image classification service via Telegram bot. A user in Telegram can either send an image or the URL of an image to the bot, and the bot will feed the image into the model to generate  predictions and send back the result to the user.


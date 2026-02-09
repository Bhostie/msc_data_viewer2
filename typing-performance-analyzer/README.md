# Typing Performance Analyzer

The aim of this project is to calculate typing performance metrics for a given sequence of keyboard interactions. 
It considers the following metrics:

 * Words per minute (WPM)
 * Keystrokes per second (KSPS)
 * Keystrokes per character (KSPC)
 * Error rate (ER)

In addition to these metrics, it distinguishes between following conditions when a user deletes one or more characters and enters another text:

 * Correcting a typing error (or typo)
 * Writing something else after changing mind

## Data Model

The expected input is a sequence of logs of the keyboard events at the character level. 
In other words, it adopts the transcription sequence paradigm by capturing the entire transcription after every
keyboard action. A keyboard log is recorded for every keyboard interaction
that either inserts or removes a character. An example log entry is given below:

```
{
  "_id" : 1619,
  "timestamp" : "1764187044257",
  "device_id" : "4daac81b-fa00-4796-8aaf-6be83de9f9a9",
  "package_name" : "com.whatsapp",
  "before_text" : "This s",
  "current_text" : "[This se]",
  "is_password" : 0
}
```

## Dependencies

 * coverage
 * nltk
 * phunspell

## Test & Coverage

```
coverage  run -m unittest discover -s test
coverage html
```

## Run

```
python main.py
```

# -*- coding: utf-8 -*-
"""app.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1k-NJXjVm3V98LSdY8FLSeXM1c18twmQB
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from pyngrok import ngrok
from langchain.schema import Generation, ChatResult
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import random
import json
from langdetect import detect, LangDetectException
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from langchain.chains import LLMChain
from langchain.llms import HuggingFacePipeline
from langchain.prompts import PromptTemplate

# Set environment variables
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_API_KEY'] = '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'

# Import the GPT-2 model and tokenizer
gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2")
gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

# Define the generation function using the GPT-2 model
def generate_text(prompt, max_length=50, temperature=0.7, num_return_sequences=1):
    input_ids = gpt2_tokenizer.encode(prompt, return_tensors="pt")
    output_ids = gpt2_model.generate(
        input_ids=input_ids,
        max_length=max_length,
        temperature=temperature,
        num_return_sequences=num_return_sequences,
        pad_token_id=gpt2_tokenizer.eos_token_id,
        early_stopping=True
    )
    generated_text = gpt2_tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return generated_text

# Define FastAPI app
app = FastAPI()

# Create a VADER sentiment analyzer
vader_analyzer = SentimentIntensityAnalyzer()

# Setup Hugging Face sentiment analysis pipeline
huggingface_sentiment_analyzer = pipeline("sentiment-analysis", model="BAAI/bge-small-en-v1.5")

# Configure the LlamaIndex embedding model
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
embedding_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Setup LangChain with Hugging Face model for advanced NLP
huggingface_pipeline = pipeline("text-generation", model="gpt2")
huggingface_llm = HuggingFacePipeline(pipeline=huggingface_pipeline)

prompt_template = PromptTemplate(
    template="Analyze the sentiment and generate a response for: {text}",
    input_variables=["text"]
)

langchain_chain = LLMChain(llm=huggingface_llm, prompt=prompt_template)

# Define response generator function for the welcome message
def welcome_message():
    return "Hi, how can I assist you today?"

# Define mindfulness exercises with explanations
mindfulness_exercises = {
    "1": "Deep Breathing Exercise: Sit or lie down comfortably. Close your eyes and take a deep breath in through your nose, counting to four. Hold your breath for a moment, then exhale slowly through your mouth, counting to six. Repeat this process for several minutes. This exercise helps calm the mind and reduce stress by focusing on the breath.",
    "2": "Body Scan Meditation: Start by focusing your attention on your toes and work your way up through your body, noticing any tension or discomfort. As you become aware of each body part, try to release any tension and relax it. Continue until you've scanned your entire body. This exercise promotes relaxation and body awareness.",
    "3": "Mindful Walking: Take a slow, deliberate walk, paying close attention to each step you take. Notice the sensations in your feet as they touch the ground, the movement of your legs, and the rhythm of your breath. Try to stay present and engaged with your surroundings. This exercise helps ground you in the present moment and can be a form of moving meditation."
}

# Define response generator function for mindfulness exercise suggestions
def suggest_mindfulness_exercises(sentiment_score):
    if sentiment_score < 0:
        return random.sample(list(mindfulness_exercises.items()), 2)
    else:
        return []

# Define predefined responses for recognized intents
intent_responses = {
    "request_help": "I'm here for you. You're not alone.",
    "express_gratitude": "You're welcome! Remember, I'm here whenever you need support.",
    "express_sadness": "I'm sorry to hear that you're feeling down. Things will get better, I promise.",
    "express_stress": "It sounds like you're feeling stressed. Let's try some mindfulness exercises to help you relax."
}

# Define file-based storage mechanism for mood tracking
MOOD_FILE = "user_moods.json"

def save_mood(username, mood):
    moods = load_moods()
    if username not in moods:
        moods[username] = []
    moods[username].append(mood)
    with open(MOOD_FILE, "w") as file:
        json.dump(moods, file)

def load_moods():
    try:
        with open(MOOD_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def get_user_moods(username):
    moods = load_moods()
    return moods.get(username, [])

# Define intent recognition function using langdetect
def recognize_intent(message):
    # Simplified approach for demonstration purposes
    if "help" in message:
        return "request_help"
    elif "thank" in message:
        return "express_gratitude"
    elif "sad" in message or "depressed" in message:
        return "express_sadness"
    elif "stress" in message or "anxious" in message:
        return "express_stress"
    else:
        return "unknown_intent"

# Generate embeddings using LlamaIndex
def generate_embeddings(text):
    return embedding_model.embed(text)

# Perform sentiment analysis with VADER, Hugging Face, and LangChain
def analyze_sentiment_with_all_models(text):
    vader_sentiment = vader_analyzer.polarity_scores(text)['compound']
    huggingface_sentiment = huggingface_sentiment_analyzer(text)[0]['score']

    # Handle LangChain result
    try:
        langchain_result = langchain_chain.run({"text": text})
        if isinstance(langchain_result, str):
            langchain_sentiment_text = langchain_result.strip()
            # Optional: implement custom logic to extract sentiment from the text if needed
            langchain_sentiment_score = None  # or some default score
        elif hasattr(langchain_result, 'generations'):
            langchain_sentiment_text = langchain_result.generations[0].text.strip()
            # Optional: implement custom logic to extract sentiment from the text if needed
            langchain_sentiment_score = None  # or some default score
        else:
            raise ValueError("Unexpected result type from LangChain")
    except Exception as e:
        logger.error(f"Error with LangChain sentiment analysis: {e}")
        langchain_sentiment_text = "Error processing sentiment."
        langchain_sentiment_score = None  # or some default score

    return vader_sentiment, huggingface_sentiment, langchain_sentiment_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Endpoint to handle user messages, generate sentiment response, suggest mindfulness exercises, and track mood
@app.get("/emotional-support-bot")
def generate_mindfulness_exercises(username: str, message: str, target_lang: str = "en"):
    # Detect language of the message
    try:
        detected_lang = detect(message)
    except LangDetectException:
        raise HTTPException(status_code=400, detail="Unable to detect language.")

    # Translate message to English if necessary (for further processing)
    if detected_lang != 'en':
        translated_message = "Translation to English is required for further processing."
    else:
        translated_message = message

    # Recognize intent
    intent = recognize_intent(translated_message)

    # Perform sentiment analysis using all models
    vader_sentiment_score, huggingface_sentiment_score, langchain_sentiment_score = analyze_sentiment_with_all_models(translated_message)
    combined_sentiment_score = (vader_sentiment_score + huggingface_sentiment_score + (langchain_sentiment_score if langchain_sentiment_score is not None else 0)) / 3

    # Suggest mindfulness exercises based on combined sentiment score
    exercise_suggestions = suggest_mindfulness_exercises(combined_sentiment_score)

    # Save user's mood
    save_mood(username, {
        "message": translated_message,
        "vader_sentiment_score": vader_sentiment_score,
        "huggingface_sentiment_score": huggingface_sentiment_score,
        "langchain_sentiment_score": langchain_sentiment_score
    })

    # Log the sentiment analysis and mood tracking
    logger.info(f"User: {username}, Message: {translated_message}, Vader Sentiment: {vader_sentiment_score}, HuggingFace Sentiment: {huggingface_sentiment_score}, LangChain Sentiment: {langchain_sentiment_score}")

    response = {
        "message": "Sentiment analysis completed.",
        "vader_sentiment_score": vader_sentiment_score,
        "huggingface_sentiment_score": huggingface_sentiment_score,
        "langchain_sentiment_score": langchain_sentiment_score,
        "intent": intent,
        "intent_response": intent_responses.get(intent, "I'm here to listen. Tell me more about how you're feeling.")
    }

    if exercise_suggestions:
        response["exercise_suggestions"] = [{"exercise_id": exercise[0], "exercise_description": exercise[1]} for exercise in exercise_suggestions]
    else:
        response["exercise_suggestions"] = "No exercises suggested as your sentiment seems positive or neutral."

    return response

# Endpoint to retrieve user mood history
@app.get("/user-moods/{username}")
def user_moods(username: str):
    moods = get_user_moods(username)
    if moods:
        return {"username": username, "moods": moods}
    else:
        return {"error": "No mood data found for the specified user."}

# Run the FastAPI app
import nest_asyncio
import uvicorn

# Allow nested event loops to run FastAPI within the notebook
nest_asyncio.apply()

# Create a public URL for the FastAPI app using ngrok
public_url = ngrok.connect(8000)
print(f"Public URL: {public_url}")

# Run the FastAPI app
uvicorn.run(app, host='0.0.0.0', port=8000)
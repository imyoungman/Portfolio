import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import string
import re
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
import syllapy
import multiprocessing

# Define the number of worker processes (adjust this number based on your system's capabilities)
num_processes = 6  # Example: Use 4 processes

# Download NLTK resources
nltk.download('punkt')


# Function to extract and save text from URL
def extract_and_save_text(url_id, url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        article_title = ''
        article_text = ''

        # Attempt to find the article title
        title_element = soup.find('h1', class_='entry-title')
        if title_element:
            article_title = title_element.text.strip()
            # Extract article text
            article_content = soup.find('div', class_='td-post-content tagdiv-type')
            if article_content is not None:
                for tag in article_content.find_all(['p', 'li']):
                    article_text += tag.text.strip() + '\n'
            else:
                article_text = "Article Content Not Found"
        if title_element is None:
            title_element = soup.find('h1', class_="tdb-title-text")
            article_title = title_element.text.strip()
            # Extract article text
            article_text = ''
            paragraphs = soup.find_all(
                lambda tag: tag.name == 'p' and tag.parent.get('class') == ['tdb-block-inner', 'td-fix-index'])
            if paragraphs:
                # Initialize an empty list to store paragraph texts
                paragraph_texts = []
                # Extract text from paragraphs
                for p in paragraphs:
                    paragraph_texts.append(p.get_text(strip=True))

                # Join all paragraph texts with newlines
                article_text = '\n'.join(paragraph_texts)

        # Create folder if it doesn't exist
        folder_name = "extracted_articles"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Save article text to file in the folder
        filename = os.path.join(folder_name, f"{url_id}.txt")
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(article_title + '\n\n')
            file.write(article_text)
        print(f"Article text saved to {filename}")
    else:
        print(f"Failed to fetch URL: {url}")


# Function to load stop words from multiple files in a folder
def load_stop_words(folder):

    stop_words = set()
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), 'r') as f:
                stop_words.update(word.strip() for word in f.readlines())
    return stop_words


# Function to load positive and negative words from files in a folder
def load_master_dictionary(folder, stop_words):
    positive_words = set()
    negative_words = set()
    for filename in os.listdir(folder):
        if filename.endswith("words.txt"):  # Assuming positive and negative words files have suffix "words.txt"
            with open(os.path.join(folder, filename), 'r') as f:
                words = [word.strip() for word in f.readlines() if word.strip() not in stop_words]
                if "positive" in filename:
                    positive_words.update(words)
                elif "negative" in filename:
                    negative_words.update(words)
    return positive_words, negative_words


# Function to clean text
def clean_text(text, stop_words):
    # Tokenize text
    tokens = word_tokenize(text)
    # Remove stopwords and punctuations
    tokens = [word.lower() for word in tokens if word.lower() not in stop_words and word not in string.punctuation]
    return tokens


# Function to compute sentiment analysis variables
def compute_sentiment_analysis(tokens, positive_words, negative_words):
    positive_score = sum(1 for word in tokens if word in positive_words)
    negative_score = sum(1 for word in tokens if word in negative_words)
    polarity_score = (positive_score - negative_score) / ((positive_score + negative_score) + 0.000001)
    subjectivity_score = (positive_score + negative_score) / (len(tokens) + 0.000001)
    return positive_score, negative_score, polarity_score, subjectivity_score


# Function to compute readability analysis variables
def compute_readability_analysis(text):
    # Tokenize text into sentences
    sentences = sent_tokenize(text)
    total_sentences = len(sentences)
    total_words = sum(len(word_tokenize(sentence)) for sentence in sentences)

    # Average Sentence Length
    average_sentence_length = total_words / total_sentences

    # Count complex words
    complex_words = [word for word in word_tokenize(text) if syllapy.count(word) > 2]
    complex_word_count = len(complex_words)
    percentage_complex_words = (complex_word_count / total_words) * 100

    # Fog Index
    fog_index = 0.4 * (average_sentence_length + percentage_complex_words)

    # Average Number of Words Per Sentence
    average_words_per_sentence = total_words / total_sentences

    # Word Count
    word_count = len(word_tokenize(text))

    # Syllable Count Per Word
    exceptions = {"es", "ed"}  # Set of exceptions
    syllables = sum(syllapy.count(word) if not word.endswith(tuple(exceptions)) else 0 for word in word_tokenize(text))
    syllable_per_word = syllables / word_count

    # Personal Pronouns
    personal_pronouns = len(re.findall(r'\b(?!(US)\b)(?:i|we|my|ours|us)\b', text, re.IGNORECASE))

    # Average Word Length
    average_word_length = sum(len(word) for word in word_tokenize(text)) / word_count

    return average_sentence_length, percentage_complex_words, fog_index, average_words_per_sentence, \
        complex_word_count, word_count, syllable_per_word, personal_pronouns, average_word_length


# Function to calculate metrics for each text file
def calculate_metrics_for_file(file_path, url_id):
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    tokens = clean_text(text, stop_words)
    positive_score, negative_score, polarity_score, subjectivity_score = compute_sentiment_analysis(tokens,
                                                                                                    positive_words,
                                                                                                    negative_words)
    average_sentence_length, percentage_complex_words, fog_index, average_words_per_sentence, \
        complex_word_count, word_count, syllable_per_word, personal_pronouns, average_word_length = compute_readability_analysis(text)

    return {
        'URL_ID': url_id,
        'POSITIVE SCORE': positive_score,
        'NEGATIVE SCORE': negative_score,
        'POLARITY SCORE': polarity_score,
        'SUBJECTIVITY SCORE': subjectivity_score,
        'AVERAGE SENTENCE LENGTH': average_sentence_length,
        'PERCENTAGE OF COMPLEX WORDS': percentage_complex_words,
        'FOG INDEX': fog_index,
        'AVERAGE NUMBER OF WORDS PER SENTENCE': average_words_per_sentence,
        'COMPLEX WORD COUNT': complex_word_count,
        'WORD COUNT': word_count,
        'SYLLABLE PER WORD': syllable_per_word,
        'PERSONAL PRONOUNS': personal_pronouns,
        'AVERAGE WORD LENGTH': average_word_length
    }


if __name__ == '__main__':
    # Read URLs from CSV file
    input_data = pd.read_excel('input.xlsx')

    # Load stop words from the StopWords folder
    stop_words = load_stop_words('StopWords')

    # Load positive and negative words from the MasterDictionary folder
    master_dictionary_directory = "MasterDictionary"
    positive_words, negative_words = load_master_dictionary(master_dictionary_directory, stop_words)

    # Create a pool of worker processes
    pool = multiprocessing.Pool(processes=num_processes)

    # Process each article using parallel processing
    results = [pool.apply_async(extract_and_save_text, args=(row['URL_ID'], row['URL'])) for _, row in input_data.iterrows()]

    # Close the pool and wait for all processes to finish
    pool.close()
    pool.join()

    # List to store metrics for each file
    metrics_list = []

    # Iterate through each file in the folder
    for filename in os.listdir('extracted_articles'):
        if filename.endswith('.txt'):  # Check if the file is a text file
            file_path = os.path.join('extracted_articles', filename)
            url_id = filename.split('.')[0]  # Assuming the URL_ID is the filename without extension
            # Calculate metrics for the file and append them to the metrics_list
            metrics_list.append(calculate_metrics_for_file(file_path, url_id))

    # Convert the metrics_list to a DataFrame
    metrics_df = pd.DataFrame(metrics_list)

    # Perform left join between metrics_df and input_data on URL_ID
    merged_df = pd.merge(input_data, metrics_df, on='URL_ID', how='left')

    # Reorder columns according to the desired order
    merged_df = merged_df[['URL_ID', 'URL', 'POSITIVE SCORE', 'NEGATIVE SCORE', 'POLARITY SCORE', 'SUBJECTIVITY SCORE',
                           'AVERAGE SENTENCE LENGTH', 'PERCENTAGE OF COMPLEX WORDS', 'FOG INDEX',
                           'AVERAGE NUMBER OF WORDS PER SENTENCE', 'COMPLEX WORD COUNT', 'WORD COUNT',
                           'SYLLABLE PER WORD', 'PERSONAL PRONOUNS', 'AVERAGE WORD LENGTH']]

    # Export DataFrame to Excel
    output_file = 'Output Data Structure.xlsx'
    merged_df.to_excel(output_file, index=False)

    print(f"Output data saved to {output_file}")

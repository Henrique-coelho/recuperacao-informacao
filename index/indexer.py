from nltk.stem.snowball import SnowballStemmer
from bs4 import BeautifulSoup
import string
import html
from nltk.tokenize import word_tokenize
import re
import os


class Cleaner:
    def __init__(self, stop_words_file: str, language: str,
                 perform_stop_words_removal: bool, perform_accents_removal: bool,
                 perform_stemming: bool):
        self.set_stop_words = self.read_stop_words(stop_words_file)

        self.stemmer = SnowballStemmer(language)
        in_table = "áéíóúâêôçãẽõü"
        out_table = "aeiouaeocaeou"
        self.accents_translation_table = {in_table[pos]:out_table[pos] for pos in range(len(in_table))}
        self.set_punctuation = set(string.punctuation)

        # flags
        self.perform_stop_words_removal = perform_stop_words_removal
        self.perform_accents_removal = perform_accents_removal
        self.perform_stemming = perform_stemming

    def html_to_plain_text(self, html_doc: str) -> str:
        soup =  BeautifulSoup(html_doc, 'html.parser')
        cleared_html = soup.get_text()
        return html.unescape(cleared_html)

    @staticmethod
    def read_stop_words(str_file) -> set:
        set_stop_words = set()
        with open(str_file, encoding='utf-8') as stop_words_file:
            for line in stop_words_file:
                arr_words = line.split(",")
                [set_stop_words.add(word) for word in arr_words]
        return set_stop_words

    def is_stop_word(self, term: str):
        return term in self.set_stop_words

    def word_stem(self, term: str):
        stemmer = SnowballStemmer(language='portuguese')
        return stemmer.stem(term)

    def remove_accents(self, term: str) -> str:
        return "".join([self.accents_translation_table.get(char, char) for char in term])

    def preprocess_word(self, term: str) -> str or None:
        return self.remove_accents(term.lower())

    def preprocess_text(self, text: str) -> str or None:
        punctuation = "!!??..."
        if text in punctuation:
            return None
        if self.perform_stop_words_removal and self.is_stop_word(text):
            return None
        
        if self.perform_accents_removal:
            text = self.preprocess_word(text)
        if self.perform_stemming:
            text = self.word_stem(text)

        return text
    
class HTMLIndexer:
    cleaner = Cleaner(stop_words_file="stopwords.txt",
                      language="portuguese",
                      perform_stop_words_removal=True,
                      perform_accents_removal=True,
                      perform_stemming=True)

    def __init__(self, index):
        self.index = index

    def text_word_count(self, plain_text: str):
        dic_word_count = {}

        words = word_tokenize(plain_text)
        for word in [token for token in re.findall(r'\w+|[^\w\s]', ' '.join(words))]:
            word = self.cleaner.preprocess_text(word)
            if word is not None:
                dic_word_count[word] = dic_word_count.get(word, 0) + 1

        return dic_word_count

    def index_text(self, doc_id: int, text_html: str):
        text = self.cleaner.html_to_plain_text(text_html)
        dic_word_count = self.text_word_count(text)
        for term_key, term_freq in dic_word_count.items():
            self.index.index(term_key, doc_id, term_freq)  
        self.index.finish_indexing()

    def index_text_dir(self, path: str):
        for str_sub_dir in os.listdir(path):
            path_sub_dir = f"{path}/{str_sub_dir}"

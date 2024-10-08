from index.indexer import *
from index.structure import *

if __name__ == "__main__":
    HTMLIndexer.cleaner = Cleaner(stop_words_file="stopwords.txt",
                        language="portuguese",
                        perform_stop_words_removal=True,
                        perform_accents_removal=True,
                        perform_stemming=False)
    indexer = HTMLIndexer(HashIndex())
    indexer.index_text_dir("wiki")

    path = "wiki_hash.idx"
    indexer.index.write(path)
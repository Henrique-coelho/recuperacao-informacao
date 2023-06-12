from index.indexer import *
from index.structure import *

if __name__ == "__main__":
    HTMLIndexer.cleaner = Cleaner(stop_words_file="stopwords.txt",
                        language="portuguese",
                        perform_stop_words_removal=True,
                        perform_accents_removal=True,
                        perform_stemming=False)
    indexer = HTMLIndexer(FileIndex())
    indexer.index_text_dir("wiki")
    counter = indexer.index.idx_file_counter

    old_path = "occur_" + str(counter) + ".idx"
    new_path = "wiki.idx"
    os.rename(old_path, new_path)


    
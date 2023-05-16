from IPython.display import clear_output
from typing import List, Set, Union
from abc import abstractmethod
from functools import total_ordering
from os import path
import os
import pickle
import gc


class Index:
    def __init__(self):
        self.dic_index = {}
        self.set_documents = set()

    def index(self, term: str, doc_id: int, term_freq: int):
        if term not in self.dic_index:
            int_term_id = None
            self.dic_index[term] = self.create_index_entry(int_term_id)
        else:
            int_term_id = self.get_term_id(term)

        if doc_id not in self.set_documents:
            self.set_documents.add(doc_id)
        self.add_index_occur(self.dic_index[term], doc_id, int_term_id, term_freq)

    @property
    def vocabulary(self) -> List[str]:
        return self.dic_index.keys()

    @property
    def document_count(self) -> int:
        return len(self.set_documents)

    @abstractmethod
    def get_term_id(self, term: str):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def create_index_entry(self, termo_id: int):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def add_index_occur(self, entry_dic_index, doc_id: int, term_id: int, freq_termo: int):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def get_occurrence_list(self, term: str) -> List:
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def document_count_with_term(self, term: str) -> int:
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    def finish_indexing(self):
        pass

    def write(self, arq_index: str):
        pass
    

    @staticmethod
    def read(arq_index: str):
        pass

    def __str__(self):
        arr_index = []
        for str_term in self.vocabulary:
            arr_index.append(f"{str_term} -> {self.get_occurrence_list(str_term)}")

        return "\n".join(arr_index)

    def __repr__(self):
        return str(self)


@total_ordering
class TermOccurrence:
    def __init__(self, doc_id: int, term_id: int, term_freq: int):
        self.doc_id = doc_id
        self.term_id = term_id
        self.term_freq = term_freq

    def write(self, idx_file):
        idx_file.write(self.doc_id.to_bytes(4, byteorder="big"))
        idx_file.write(self.term_id.to_bytes(4, byteorder="big"))
        idx_file.write(self.term_freq.to_bytes(4, byteorder="big"))

    def __hash__(self):
        return hash((self.doc_id, self.term_id))

    def __eq__(self, other_occurrence: "TermOccurrence"):
        if(other_occurrence is None):
            return False
        return self.doc_id == other_occurrence.doc_id and self.term_id == other_occurrence.term_id and self.term_freq == other_occurrence.term_freq

    def __lt__(self, other_occurrence: "TermOccurrence"):
        if(other_occurrence is None):
            return True
        if(self.term_id < other_occurrence.term_id):
            return True
        return self.doc_id < other_occurrence.doc_id

    def __str__(self):
        return f"( doc: {self.doc_id} term_id:{self.term_id} freq: {self.term_freq})"

    def __repr__(self):
        return str(self)


# HashIndex é subclasse de Index
class HashIndex(Index):
    def get_term_id(self, term: str):
        return self.dic_index[term][0].term_id

    def create_index_entry(self, termo_id: int) -> List:
        return []

    def add_index_occur(self, entry_dic_index: List[TermOccurrence], doc_id: int, term_id: int, term_freq: int):
        entry_dic_index.append(TermOccurrence(doc_id,term_id,term_freq))

    def get_occurrence_list(self, term: str) -> List:
        if term in self.dic_index.keys():
            return self.dic_index[term]
        else:
            return []

    def document_count_with_term(self, term: str) -> int:
        count = 0
        if term not in self.dic_index.keys():
            return 0
        for occurances in self.dic_index[term]:
            count += 1
        return count


class TermFilePosition:
    def __init__(self, term_id: int, term_file_start_pos: int = None, doc_count_with_term: int = None):
        self.term_id = term_id

        # a serem definidos após a indexação
        self.term_file_start_pos = term_file_start_pos
        self.doc_count_with_term = doc_count_with_term

    def __str__(self):
        return f"term_id: {self.term_id}, doc_count_with_term: {self.doc_count_with_term}, term_file_start_pos: {self.term_file_start_pos}"

    def __repr__(self):
        return str(self)


class FileIndex(Index):
    TMP_OCCURRENCES_LIMIT = 1000000

    def __init__(self):
        super().__init__()

        self.lst_occurrences_tmp = [None]*FileIndex.TMP_OCCURRENCES_LIMIT
        self.idx_file_counter = 0
        self.str_idx_file_name = None

        # metodos auxiliares para verifica o tamanho da lst_occurrences_tmp
        self.idx_tmp_occur_last_element  = -1
        self.idx_tmp_occur_first_element = 0
        
    def get_tmp_occur_size(self):
        """Retorna o tamanho da lista temporária de ocorrências"""
        return self.idx_tmp_occur_last_element - self.idx_tmp_occur_first_element + 1

    def get_term_id(self, term: str):
        return self.dic_index[term].term_id

    def create_index_entry(self, term_id: int) -> TermFilePosition:
        return TermFilePosition(term_id=term_id)


    def add_index_occur(self, entry_dic_index: TermFilePosition, doc_id: int, term_id: int, term_freq: int):
        #complete aqui adicionando um novo TermOccurrence na lista lst_occurrences_tmp
        #não esqueça de atualizar a(s) variável(is) auxiliares apropriadamente
        
        if self.idx_tmp_occur_last_element+1<FileIndex.TMP_OCCURRENCES_LIMIT:
            self.lst_occurrences_tmp[self.idx_tmp_occur_last_element+1] = TermOccurrence(doc_id=doc_id,term_id=term_id, term_freq=term_freq)
            self.idx_tmp_occur_last_element += 1
        else:
            self.save_tmp_occurrences()

    def next_from_list(self) -> TermOccurrence:
        if self.get_tmp_occur_size() > 0:
            # obtenha o proximo da lista e armazene em nex_occur
            # não esqueça de atualizar a(s) variável(is) auxiliares apropriadamente
            next_occur = self.lst_occurrences_tmp[self.idx_tmp_occur_first_element]
            self.lst_occurrences_tmp[self.idx_tmp_occur_first_element] = None
            self.idx_tmp_occur_first_element += 1
            return next_occur
        else:
            return None

    def next_from_file(self, file_pointer) -> TermOccurrence:
        # next_from_file = pickle.load(file_idx)
        bytes_doc_id = int.from_bytes(file_pointer.read(4), byteorder="big")
        if not bytes_doc_id:
            return None
        bytes_term_id = int.from_bytes(file_pointer.read(4), byteorder="big")
        if not bytes_doc_id:
            return None
        bytes_term_freq = int.from_bytes(file_pointer.read(4), byteorder="big")
        if not bytes_doc_id:
            return None

        return TermOccurrence(bytes_doc_id, bytes_term_id, bytes_term_freq)

    def save_tmp_occurrences(self):

        # Ordena pelo term_id, doc_id
        #    Para eficiência, todo o código deve ser feito com o garbage collector desabilitado gc.disable()
        gc.disable()

        """comparar sempre a primeira posição
        da lista com a primeira posição do arquivo usando os métodos next_from_list e next_from_file
        e use o método write do TermOccurrence para armazenar cada ocorrencia do novo índice ordenado"""

        self.idx_file_counter += 1
        new_str_index_file_name = "occur_index_" + str(self.idx_file_counter)

        if self.str_idx_file_name is not None:
            file_term = self.next_from_file(self.str_idx_file_name)
            while file_term is not None:
                file_term.write()
                file_term = self.next_from_file(self.str_idx_file_name)

        list_term = self.next_from_list()
        while list_term is not None:     
            list_term.write()
            list_term = self.next_from_list()

        self.str_idx_file_name = new_str_index_file_name
        
        self.lst_occurrences_tmp = [None]*FileIndex.TMP_OCCURRENCES_LIMIT

        self.idx_tmp_occur_last_element  = -1
        self.idx_tmp_occur_first_element = 0

        gc.enable()

    def finish_indexing(self):
        if len(self.lst_occurrences_tmp) > 0:
            self.save_tmp_occurrences()

        # Sugestão: faça a navegação e obetenha um mapeamento
        # id_termo -> obj_termo armazene-o em dic_ids_por_termo
        # obj_termo é a instancia TermFilePosition correspondente ao id_termo
        dic_ids_por_termo = {}
        for str_term, obj_term in self.dic_index.items():
            pass

        with open(self.str_idx_file_name, 'rb') as idx_file:
            # navega nas ocorrencias para atualizar cada termo em dic_ids_por_termo
            # apropriadamente
            pass

    def get_occurrence_list(self, term: str) -> List:
        return []

    def document_count_with_term(self, term: str) -> int:
        return 0

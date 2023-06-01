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
            # Próximo indice
            int_term_id = len(self.dic_index)
            self.dic_index[term] = self.create_index_entry(int_term_id)
        else:
            int_term_id = self.get_term_id(term)

        self.set_documents.add(doc_id)
        self.add_index_occur(self.dic_index[term], doc_id, int_term_id, term_freq)

    @property
    def vocabulary(self) -> List[str]:
        indexArr = []
        for i in self.dic_index:
            indexArr.append(i)
        return indexArr

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
        pickle_out = open(arq_index,"wb")
        pickle.dump(self, pickle_out)
        pickle_out.close()
    

    @staticmethod
    def read(arq_index: str):
        pickle_in = open(arq_index,"rb")
        return pickle.load(pickle_in)

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
        idx_file.write(self.term_id.to_bytes(4,byteorder="big"))
        idx_file.write(self.doc_id.to_bytes(4,byteorder="big"))
        idx_file.write(self.term_freq.to_bytes(4,byteorder="big"))

    def __hash__(self):
        return hash((self.doc_id, self.term_id))

    def __eq__(self, other_occurrence: "TermOccurrence"):
        if other_occurrence is None:
            return False
        if (self.doc_id == other_occurrence.doc_id) and (self.term_id == other_occurrence.term_id):
            return True
        return False

    def __lt__(self, other_occurrence: "TermOccurrence"):
        if other_occurrence is None:
            return False
        if (self.term_id < other_occurrence.term_id):
            return True
        else:
            if (self.term_id == other_occurrence.term_id):
                if (self.doc_id < other_occurrence.doc_id):
                    return True
        return False

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
        index_occur = TermOccurrence(doc_id, term_id, term_freq)
        if entry_dic_index is None:
            entry_dic_index = [index_occur]
        else:
            entry_dic_index.append(index_occur)

             

    def get_occurrence_list(self, term: str) -> List:
        if term not in self.dic_index:
            return []
        return self.dic_index[term]

    def document_count_with_term(self, term: str) -> int:
        occ = self.get_occurrence_list(term)
        if len(occ) == 0:
            return 0
        return len(occ)


class TermFilePosition:
    def __init__(self, term_id: int, term_file_start_pos: int = None, doc_count_with_term: int = None):
        self.term_id = term_id

        # a serem definidos após a indexação
        self.term_file_start_pos = term_file_start_pos
        self.doc_count_with_term = doc_count_with_term

        if self.term_file_start_pos is None:
            self.term_file_start_pos = 0
        if self.doc_count_with_term is None:
            self.doc_count_with_term = 0

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
        self.str_idx_file_name = "occur_idx_file"

        # metodos auxiliares para verifica o tamanho da lst_occurrences_tmp
        self.idx_tmp_occur_last_element  = -1
        self.idx_tmp_occur_first_element = 0
        
    def get_tmp_occur_size(self):
        """Retorna o tamanho da lista temporária de ocorrências"""
        return self.idx_tmp_occur_last_element - self.idx_tmp_occur_first_element + 1

    def get_term_id(self, term: str):
        return self.dic_index[term].term_id

    def create_index_entry(self, term_id: int) -> TermFilePosition:
        return TermFilePosition(term_id)

    def add_index_occur(self, entry_dic_index: TermFilePosition, doc_id: int, term_id: int, term_freq: int):
        #complete aqui adicionando um novo TermOccurrence na lista lst_occurrences_tmp
        #não esqueça de atualizar a(s) variável(is) auxiliares apropriadamente
        occ = TermOccurrence(doc_id, term_id, term_freq)

        if (self.idx_tmp_occur_last_element + 1 < FileIndex.TMP_OCCURRENCES_LIMIT):
            self.lst_occurrences_tmp[self.idx_tmp_occur_last_element + 1] = occ
            self.idx_tmp_occur_last_element += 1
        else:
            self.save_tmp_occurrences()

    def next_from_list(self) -> TermOccurrence:
            # obtenha o proximo da lista e armazene em nex_occur
            # não esqueça de atualizar a(s) variável(is) auxiliares apropriadamente
        if self.get_tmp_occur_size() > 0:
            next_from_list = self.lst_occurrences_tmp[self.idx_tmp_occur_first_element]
            self.lst_occurrences_tmp[self.idx_tmp_occur_first_element] = None
            self.idx_tmp_occur_first_element += 1

            return next_from_list
        return None

    def next_from_file(self, file_pointer) -> TermOccurrence:
        # next_from_file = pickle.load(file_idx)
        if file_pointer is None:
            return None
        
        doc_id = int.from_bytes(file_pointer.read(4), byteorder='big')
        term_id = int.from_bytes(file_pointer.read(4), byteorder='big')
        term_freq = int.from_bytes(file_pointer.read(4), byteorder='big')

        if doc_id == 0 or term_freq == 0 or term_id == 0:
            return None

        return TermOccurrence(term_id, doc_id, term_freq)

    def save_tmp_occurrences(self):

        # Para eficiência, todo o código deve ser feito com o garbage collector desabilitado gc.disable()
        gc.disable()

        self.lst_occurrences_tmp.sort(key=lambda e: (e is None, e))

        old_file = None if self.idx_file_counter == 0 else open(
            self.str_idx_file_name, 'rb')
        self.idx_file_counter += 1
        self.str_idx_file_name = f"occur_idx_file_{self.idx_file_counter}.idx"

        new_file = open(self.str_idx_file_name, 'wb')

        """
            Comparar sempre a primeira posição da lista com a primeira posição do arquivo usando 
            os métodos next_from_list e next_from_filee use o método write do TermOccurrence para 
            armazenar cada ocorrencia do novo índice ordenado
        """
        nxt_list = self.next_from_list()
        nxt_file = self.next_from_file(old_file)

        while nxt_file and nxt_list:
            if nxt_list > nxt_file:
                nxt_file.write(new_file)
                nxt_file = self.next_from_file(old_file)
            else:
                nxt_list.write(new_file)
                nxt_list = self.next_from_list()
        while nxt_list:
            nxt_list.write(new_file)
            nxt_list = self.next_from_list()
        while nxt_file:
            nxt_file.write(new_file)
            nxt_file = self.next_from_file(old_file)
        self.idx_tmp_occur_first_element = 0
        self.idx_tmp_occur_last_element = -1

        if old_file is not None:
            old_file.close()
        new_file.close()

        gc.enable()

    def finish_indexing(self):
        if len(self.lst_occurrences_tmp) > 0:
            self.save_tmp_occurrences()

        # Sugestão: faça a navegação e obetenha um mapeamento
        # id_termo -> obj_termo armazene-o em dic_ids_por_termo
        # obj_termo é a instancia TermFilePosition correspondente ao id_termo
        dic_ids_por_termo = {}
        print("### finish_indexing ###")
        for str_term, obj_term in self.dic_index.items():
            dic_ids_por_termo[obj_term.term_id] = obj_term
            print(f"obj_term: {obj_term}")
        print("")

        with open(self.str_idx_file_name, 'rb') as idx_file:
            # navega nas ocorrencias para atualizar cada termo em dic_ids_por_termo
            # apropriadamente
            next_file = self.next_from_file(idx_file)
            position = 0
            while (next_file):
                item_dic = dic_ids_por_termo[next_file.term_id]

                # quantas vezes o termo aparece no arquivo
                new_count = item_dic.doc_count_with_term
                if new_count is None:
                    new_count = 0
                item_dic.doc_count_with_term = new_count + 1

                if item_dic.term_file_start_pos is None:
                    item_dic.term_file_start_pos = position * 12
                
                # atualiza posição
                dic_ids_por_termo[next_file.term_id] = item_dic
                next_file = self.next_from_file(idx_file)
                position = position + 1


    def get_occurrence_list(self,term: str)->List:
        occ_list = []

        if term not in self.dic_index:
            return occ_list
        else:
            obj_term_file_position = self.dic_index[term]
            search_term = obj_term_file_position.term_id

            with open(self.str_idx_file_name, 'rb') as idx_file:
                print(f'self.dic_index: {self.dic_index}')
                idx_file.seek(self.dic_index[term].term_file_start_pos)
                next_file = self.next_from_file(idx_file)
                while(next_file is not None and search_term == next_file.term_id):
                    occ_list.append(next_file)
                    next_file = self.next_from_file(idx_file)
            return occ_list
    
    
    def document_count_with_term(self,term:str) -> int:
        if term in self.dic_index:
            return self.dic_index[term].doc_count_with_term
        else: 
            return 0
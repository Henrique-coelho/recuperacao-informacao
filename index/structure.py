from IPython.display import clear_output
from typing import List, Set, Union
from abc import abstractmethod
from functools import total_ordering
from os import path
import os
import json
import gc
import pickle


class Index:
    def __init__(self):
        self.dic_index = {}
        self.set_documents = set()

    def index(self, term:str, doc_id:int, term_freq:int):
        if term not in self.dic_index:
            int_term_id = len(self.dic_index)
            self.dic_index[term] = self.create_index_entry(int_term_id)
        else:
            int_term_id = self.get_term_id(term)

        self.add_index_occur(self.dic_index[term], doc_id, int_term_id, term_freq)
        self.set_documents.add(doc_id)

    @property
    def vocabulary(self) -> List:
        return self.dic_index.keys()

    @property
    def document_count(self) -> int:
        return len(self.set_documents)

    def write(self, arq_index: str):
        with open(arq_index,"wb") as arquivo:
            pickle.dump(self, arquivo)
    
    @staticmethod
    def read(arq_index: str):
        with open(arq_index,"rb") as arquivo:
            return pickle.load(arquivo)

    """            
        def from_json(self, arq_index:str):
            with open(arq_index) as json_file:
                dic_index_read = json.load(json_file)
                for term, lista_ocorrencia in dic_index_read.items():
                    self.dic_index[term] = [None]*len(lista_ocorrencia)
                    for i,occur in enumerate(lista_ocorrencia):
                        self.dic_index[term][i] = TermOccurrence(occur[0], occur[1], occur[2])
        
        def to_json(self, arq_index:str):
            dic_index_to_write = {}
            for term, lista_ocorrencia in self.dic_index.items():
                    dic_index_to_write = [None]*len(lista_ocorrencia)
                    for i,occur in enumerate(lista_ocorrencia):
                        dic_index_to_write[term][i] = (occur[0], occur[1], occur[2])
            with open(arq_index, "w") as json_file:
                json.dump(dic_index_to_write, json_file)
    """    
    @abstractmethod
    def to_index_entry(self, occur) -> List:
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def to_list(self, occur) -> List:
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def get_term_id(self, term:str):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def create_index_entry(self, termo_id:int):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def add_index_occur(self, entry_dic_index, doc_id:int, term_id:int, freq_termo:int):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def get_occurrence_list(self, term:str) -> List:
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    @abstractmethod
    def document_count_with_term(self,term:str) -> int:
         raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    def finish_indexing(self):
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
    def __init__(self,doc_id:int,term_id:int, term_freq:int):
        self.doc_id = doc_id
        self.term_id = term_id
        self.term_freq = term_freq

    def write(self, idx_file):
        idx_file.write(self.doc_id.to_bytes(4,byteorder="big"))
        idx_file.write(self.term_id.to_bytes(4,byteorder="big"))
        idx_file.write(self.term_freq.to_bytes(4,byteorder="big"))
        #pass

    def __hash__(self):
    	return hash((self.doc_id,self.term_id))

    def __eq__(self,other_occurrence:"TermOccurrence"):
        if not other_occurrence:
            return False
        return self.doc_id == other_occurrence.doc_id and self.term_id == other_occurrence.term_id

    def __lt__(self,other_occurrence:"TermOccurrence"):
        if other_occurrence is None:
            return True
        return self.term_id <other_occurrence.term_id or (self.term_id==other_occurrence.term_id and self.doc_id<other_occurrence.doc_id)

    def __str__(self):
        return f"( doc: {self.doc_id} term_id:{self.term_id} freq: {self.term_freq})"

    def __repr__(self):
        return str(self)


#HashIndex é subclasse de Index
class HashIndex(Index):

    def get_term_id(self, term:str):
        return self.dic_index[term][0].term_id

    def create_index_entry(self, termo_id:int) -> List:
        return []

    def add_index_occur(self, entry_dic_index:List, doc_id:int, term_id:int, term_freq:int):
        entry_dic_index.append(TermOccurrence(doc_id, term_id, term_freq))

    def get_occurrence_list(self,term: str)->List:
        return self.dic_index[term] if term in self.dic_index else []

    def document_count_with_term(self,term:str) -> int:
        return len(self.dic_index[term])  if term in self.dic_index else 0



class TermFilePosition:
    def __init__(self,term_id:int,  term_file_start_pos:int=None, doc_count_with_term:int = None):
        self.term_id = term_id

        #a serem definidos após a indexação
        self.term_file_start_pos = term_file_start_pos
        self.doc_count_with_term = doc_count_with_term

    def __str__(self):
        return f"term_id: {self.term_id}, doc_count_with_term: {self.doc_count_with_term}, term_file_start_pos: {self.term_file_start_pos}"
    def __repr__(self):
        return str(self)




class FileIndex(Index):

    TMP_OCCURRENCES_LIMIT = 339000#1000000

    def __init__(self):
        super().__init__()
        self.lst_occurrences_tmp = [None]*FileIndex.TMP_OCCURRENCES_LIMIT
        self.idx_file_counter = 0
        self.str_idx_file_name = "occur_idx_file"

        self.idx_tmp_occur_first_element = 0
        self.idx_tmp_occur_last_element  = -1
        

    def get_term_id(self, term:str):
        return self.dic_index[term].term_id

    def create_index_entry(self, term_id:int) -> TermFilePosition:
        return  TermFilePosition(term_id)

    def add_index_occur(self, entry_dic_index:TermFilePosition,  doc_id:int, term_id:int, term_freq:int):
        self.idx_tmp_occur_last_element += 1
        self.lst_occurrences_tmp[self.idx_tmp_occur_last_element] = TermOccurrence(doc_id,term_id,term_freq)
        
        if self.get_tmp_occur_size() >= self.TMP_OCCURRENCES_LIMIT:
            self.save_tmp_occurrences()

    def get_tmp_occur_size(self):
        return  self.idx_tmp_occur_last_element - self.idx_tmp_occur_first_element + 1
    
    def next_from_list(self) -> TermOccurrence:

        if self.get_tmp_occur_size() > 0:
            next_occur = self.lst_occurrences_tmp[self.idx_tmp_occur_first_element]
            self.idx_tmp_occur_first_element += 1
            return next_occur
        else:
            return None
        #return self.lst_occurrences_tmp.pop(0) if len(self.lst_occurrences_tmp)>0 else None

    def next_from_file(self,file_idx) -> TermOccurrence:
        #next_from_file = pickle.load(file_idx)
        bytes_doc_id = file_idx.read(4)
        if not bytes_doc_id:
            return None
        doc_id = int.from_bytes(bytes_doc_id,byteorder="big")
        term_id = int.from_bytes(file_idx.read(4),byteorder="big")
        term_freq = int.from_bytes(file_idx.read(4),byteorder="big")

        return TermOccurrence(doc_id, term_id, term_freq)


    def save_tmp_occurrences(self):


        #Para eficiencia, todo o codigo deve ser feito com o garbage
        #collector desabilitado
        gc.disable()
        #ordena pelo term_id, doc_id
        self.lst_occurrences_tmp.sort(key=lambda e: (e is None, e))
        #faz o ordenação externa
        str_last_idx_file = self.str_idx_file_name
        str_new_idx_file = f"occur_{self.idx_file_counter+1}.idx"
        #10 MB de buffer
        with open(str_new_idx_file,"wb") as idx_new_file:
            #inicializa
            file_last_idx = None
            next_from_file = None
            num_occur_saved = 0

            if path.exists(str_last_idx_file):
                file_size = os.path.getsize(str_last_idx_file)
                file_last_idx = open(str_last_idx_file,"rb")
                next_from_file = self.next_from_file(file_last_idx)
            
            next_from_list = self.next_from_list()

            #enquanto tanto a lista quanto o arquivo possuirem entrada
            while next_from_list and next_from_file:
                #print(f"Comparando: {next_from_list} e {next_from_file} ")
                if next_from_list>next_from_file:
                    occur = next_from_file
                    next_from_file = self.next_from_file(file_last_idx)
                else:
                    occur = next_from_list
                    next_from_list = self.next_from_list()
                #print(f"Adicionou {occur}")
                occur.write(idx_new_file)
                num_occur_saved += 1
                #self.print_occurrence_writing_status(str_new_idx_file,(list_total-len(self.lst_occurrences_tmp))/list_total,\
                #                                    idx_new_file.tell()/file_size)
            #termina a lista (O arquivo ja tinha terminado)
            while next_from_list:
                next_from_list.write(idx_new_file)
                next_from_list = self.next_from_list()
                num_occur_saved += 1
                #self.print_occurrence_writing_status(str_new_idx_file,(list_total-len(self.lst_occurrences_tmp))/list_total,1)
            #termina o arquivo (a lista terminou )
            while next_from_file:
                next_from_file.write(idx_new_file)
                next_from_file = self.next_from_file(file_last_idx)
                num_occur_saved += 1
                #self.print_occurrence_writing_status(str_new_idx_file,1, idx_new_file.tell()/file_size)
            #print(f"{num_occur_saved} ocorrências salvas  no arquivo {str_new_idx_file}...")
            #feche o arquivo, se necessário
            if file_last_idx:
                file_last_idx.close()
                #exclui os arquivo de indice antigo
                os.remove(str_last_idx_file)


        #atualiza o contador
        self.idx_file_counter += 1

        #limpa a lista
        self.idx_tmp_occur_last_element  = -1
        self.idx_tmp_occur_first_element = 0
        
        #atualiza o nome do arquivo de indice
        self.str_idx_file_name = str_new_idx_file
        #print(f"Nome do indice: {self.str_idx_file_name}")
        gc.enable()

    def finish_indexing(self):
        if len(self.lst_occurrences_tmp) > 0:
            self.save_tmp_occurrences()

        #faça a navegação para obter o mapa de ids por termo
        dic_ids_por_termo = {}
        for str_term,obj_term in self.dic_index.items():
            dic_ids_por_termo[obj_term.term_id] = obj_term
        #print(dic_ids_por_termo)
        with open(self.str_idx_file_name,'rb') as idx_file:
            #navega nas ocorrencias
            occur = self.next_from_file(idx_file)
            obj_last_term = dic_ids_por_termo[occur.term_id]
            obj_last_term.term_file_start_pos = 0
            num_docs = 0
            last_pos = 0
            while occur != None:
                if obj_last_term.term_id != occur.term_id:
                    last_term_id = occur.term_id
                    #atualiza o anterior com o numero de documentos
                    obj_last_term.doc_count_with_term = num_docs

                    #taualiza a posição do atual
                    obj_term = dic_ids_por_termo[occur.term_id]
                    obj_term.term_file_start_pos = last_pos

                    #atualiza o last pos e o numdoc
                    obj_last_term = obj_term
                    num_docs = 1
                else:
                    num_docs += 1

                #prepara para a proxima iteração
                last_pos = idx_file.tell()
                occur=self.next_from_file(idx_file)

            obj_last_term.doc_count_with_term = num_docs

    def get_occurrence_list(self,term: str)->List:
        if term not in self.dic_index:
            return []
        obj_term = self.dic_index[term]

        with open(self.str_idx_file_name,'rb') as idx_file:
            idx_file.seek(obj_term.term_file_start_pos)
            arr_occur = []
            for i in range(obj_term.doc_count_with_term):
                arr_occur.append(self.next_from_file(idx_file))

            return arr_occur

    def document_count_with_term(self,term:str) -> int:
        if term not in self.dic_index:
            return 0
        obj_term = self.dic_index[term]
        return obj_term.doc_count_with_term

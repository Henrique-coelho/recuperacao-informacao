from typing import List
from abc import abstractmethod
from typing import List, Set,Mapping
from index.structure import TermOccurrence
import math
import numpy as np
from enum import Enum

class IndexPreComputedVals():
    def __init__(self,index):
        self.index = index
        self.precompute_vals()

    def precompute_vals(self):
        """
        Inicializa os atributos por meio do indice (idx):
            doc_count: o numero de documentos que o indice possui
            document_norm: A norma por documento (cada termo é presentado pelo seu peso (tfxidf))
        """
        self.document_norm = {}
        doc_count = self.index.document_count
        for doc_id in self.index.set_documents:
            tf_idf_per_term = []
            for term in self.index.vocabulary:
                
                occurences = self.index.get_occurrence_list(term)
                term_freq_query = [occur.term_freq for occur in occurences if occur.doc_id == doc_id and occur.term_id == self.index.get_term_id(term)]

                term_freq = term_freq_query[0] if len(term_freq_query) > 0 else 0
                num_docs_with_term = len(occurences)
                
                tf_idf_per_term.append(VectorRankingModel.tf_idf(doc_count, term_freq, num_docs_with_term))
           
            norm = math.sqrt(np.square(tf_idf_per_term).sum())
            self.document_norm[doc_id] = norm
        
        self.doc_count = doc_count
        
class RankingModel():
    @abstractmethod
    def get_ordered_docs(self,query:Mapping[str,TermOccurrence],
                              docs_occur_per_term:Mapping[str,List[TermOccurrence]]) -> (List[int], Mapping[int,float]):
        raise NotImplementedError("Voce deve criar uma subclasse e a mesma deve sobrepor este método")

    def rank_document_ids(self,documents_weight):
        doc_ids = list(documents_weight.keys())
        doc_ids.sort(key= lambda x:-documents_weight[x])
        return doc_ids

class OPERATOR(Enum):
  AND = 1
  OR = 2
    
#Atividade 1
class BooleanRankingModel(RankingModel):
    def __init__(self,operator:OPERATOR):
        self.operator = operator

    def intersection_all(self,map_lst_occurrences:Mapping[str,List[TermOccurrence]]) -> List[int]:
        set_ids = set()

        for _, lst_occurrences in map_lst_occurrences.items():
            doc_ids = set([occur.doc_id for occur in lst_occurrences])
            if not set_ids:
                set_ids = doc_ids
            else:
                set_ids = set_ids & doc_ids
            
        return set_ids
    
    def union_all(self,map_lst_occurrences:Mapping[str,List[TermOccurrence]]) -> List[int]:
        set_ids = set()

        for _, lst_occurrences in map_lst_occurrences.items():
            doc_ids = set([occur.doc_id for occur in lst_occurrences])
            if not set_ids:
                set_ids = doc_ids
            else:
                set_ids = set_ids | doc_ids

        return set_ids

    def get_ordered_docs(self,query:Mapping[str,TermOccurrence],
                              map_lst_occurrences:Mapping[str,List[TermOccurrence]]) -> (List[int], Mapping[int,float]):
        """Considere que map_lst_occurrences possui as ocorrencias apenas dos termos que existem na consulta"""
        if self.operator == OPERATOR.AND:
            return self.intersection_all(map_lst_occurrences),None
        else:
            return self.union_all(map_lst_occurrences),None

#Atividade 2
class VectorRankingModel(RankingModel):

    def __init__(self,idx_pre_comp_vals:IndexPreComputedVals):
        self.idx_pre_comp_vals = idx_pre_comp_vals

    @staticmethod
    def tf(freq_term:int) -> float:
        return 1 + math.log(freq_term, 2)

    @staticmethod
    def idf(doc_count:int, num_docs_with_term:int )->float:
        if num_docs_with_term > 0:
            return math.log(doc_count/num_docs_with_term, 2)
        return 0

    @staticmethod
    def tf_idf(doc_count:int, freq_term:int, num_docs_with_term) -> float:
        if freq_term <= 0:
            return 0
        
        tf = VectorRankingModel.tf(freq_term)
        idf = VectorRankingModel.idf(doc_count, num_docs_with_term)
        
        return tf*idf

    def get_ordered_docs(self,query:Mapping[str,TermOccurrence],docs_occur_per_term:Mapping[str,List[TermOccurrence]]) -> (List[int], Mapping[int,float]):
            
            doc_count = self.idx_pre_comp_vals.doc_count
            doc_ids = self.idx_pre_comp_vals.document_norm.keys()

            tf_idf = {}
            num_docs_with_term_per_term = {}

            for term, occurences in docs_occur_per_term.items():
                num_docs_with_term_per_term[term] = len(occurences)
                num_docs_with_term = len(occurences)
                term_tf_idf = {}

                for doc_id in doc_ids:
                    term_freq_query = [occur.term_freq for occur in occurences if occur.doc_id == doc_id]
                    
                    term_freq = term_freq_query[0] if len(term_freq_query) > 0 else 0
                    num_docs_with_term = len(occurences)

                    term_tf_idf[doc_id] = VectorRankingModel.tf_idf(doc_count, term_freq, num_docs_with_term)
                tf_idf[term] = term_tf_idf

            documents_weight = {}
            for doc_id in doc_ids:
                sim = 0
                for term,occurence in query.items():
                    if term in num_docs_with_term_per_term:
                        query_tf_idf = VectorRankingModel.tf_idf(doc_count, occurence.term_freq, num_docs_with_term_per_term.get(term, 0))
                        sim += tf_idf[term][doc_id] * query_tf_idf
                
                if sim != 0:
                    sim /= self.idx_pre_comp_vals.document_norm[doc_id]
                    documents_weight[doc_id] = sim

            #retona a lista de doc ids ordenados de acordo com o TF IDF
            return self.rank_document_ids(documents_weight),documents_weight


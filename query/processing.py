from collections import Counter
from typing import List, Set,Mapping
from nltk.tokenize import word_tokenize

from util.time import CheckTime
from query.ranking_models import OPERATOR, BooleanRankingModel, RankingModel,VectorRankingModel, IndexPreComputedVals
from index.structure import Index, TermOccurrence
from index.indexer import Cleaner

class QueryRunner:
	def __init__(self,ranking_model:RankingModel,index:Index, cleaner:Cleaner):
		self.ranking_model = ranking_model
		self.index = index
		self.cleaner = cleaner


	def get_relevance_per_query(self=None) -> Mapping[str,Set[int]]:
		"""
		Adiciona a lista de documentos relevantes para um determinada query (os documentos relevantes foram
		fornecidos no ".dat" correspondente. Por ex, belo_horizonte.dat possui os documentos relevantes da consulta "Belo Horizonte"

		"""
		dic_relevance_docs = {}
		for arquiv in ["belo_horizonte","irlanda","sao_paulo"]:
			with open(f"relevant_docs/{arquiv}.dat") as arq:
				dic_relevance_docs[arquiv] = set(arq.readline().split(","))
		return dic_relevance_docs

	def count_topn_relevant(self,n:int,respostas:List[int],doc_relevantes:Set[int]) -> int:
		"""
		Calcula a quantidade de documentos relevantes na top n posições da lista lstResposta que é a resposta a uma consulta
		Considere que respostas já é a lista de respostas ordenadas por um método de processamento de consulta (BM25, Modelo vetorial).
		Os documentos relevantes estão no parametro docRelevantes
		"""
		#print(f"Respostas: {respostas} doc_relevantes: {doc_relevantes}")
		relevance_count = 0

		# Iterar pelas n primeiras posições da lista de respostas
		if len(respostas) == 0:
			return relevance_count
		for doc in doc_relevantes:
			doc_int = int(doc)         
			posicao = 0

			# Verifica se tá em respostas
			while (posicao < len(respostas)) and (posicao < n):
				if doc_int == respostas[posicao]:
					# se sim, adiciona em relevance_count
					relevance_count = relevance_count + 1
				posicao = posicao + 1

		return relevance_count

	def compute_precision_recall(self, n:int, lst_docs:List[int],relevant_docs:Set[int]) -> (float,float):
		c_topn_relevant = self.count_topn_relevant(n,lst_docs,relevant_docs)
		precision = float(c_topn_relevant/n)
		recall = float(c_topn_relevant/len(relevant_docs))
		return precision, recall
	
	def get_query_term_occurence(self, query:str) -> Mapping[str,TermOccurrence]:
		"""
			Preprocesse a consulta da mesma forma que foi preprocessado o texto do documento (use a classe Cleaner para isso).
			E transforme a consulta em um dicionario em que a chave é o termo que ocorreu
			e o valor é uma instancia da classe TermOccurrence (feita no trabalho prático passado).
			Coloque o docId como None.
			Caso o termo nao exista no indic, ele será desconsiderado.
		"""
		map_term_occur = {}
		dic_count = {}

		preprocess_text = self.cleaner.preprocess_text(query)

		tokenized_text = word_tokenize(
			preprocess_text, 
			language="portuguese"
		)

		for tk in tokenized_text: 	
			term = self.cleaner.preprocess_word(tk)
			if term != None:
				if not(term in dic_count):
					dic_count[term] = 0
				dic_count[term] += 1

		for key, idx in dic_count.items():
			occurrence_list = self.index.get_occurrence_list(key)
			if occurrence_list:
				map_term_occur[key] = TermOccurrence(
					None, #doc_id
					self.index.get_term_id(key), #doc_id
					idx #term
				)
				
		return map_term_occur

	def get_occurrence_list_per_term(self, terms:List) -> Mapping[str, List[TermOccurrence]]:
		"""
			Retorna dicionario a lista de ocorrencia no indice de cada termo passado como parametro.
			Caso o termo nao exista, este termo possuirá uma lista vazia
		"""
		dic_terms = {}
		for term in terms:
			occur_list = self.index.get_occurrence_list(term)

			if occur_list == None:
				dic_terms[term] = []
			else:
				dic_terms[term] = occur_list
		return dic_terms
	
	def get_docs_term(self, query:str) -> List[int]:
		"""
			A partir do indice, retorna a lista de ids de documentos desta consulta
			usando o modelo especificado pelo atributo ranking_model
		"""
		#Obtenha, para cada termo da consulta, sua ocorrencia por meio do método get_query_term_occurence
		dic_query_occur = self.get_query_term_occurence(query)

		#obtenha a lista de ocorrencia dos termos da consulta
		dic_occur_per_term_query = self.get_occurrence_list_per_term(dic_query_occur.keys())


		#utilize o ranking_model para retornar o documentos ordenados considrando dic_query_occur e dic_occur_per_term_query
		return self.ranking_model.get_ordered_docs(dic_query_occur, dic_occur_per_term_query)

	@staticmethod
	def runQuery(query:str, indice:Index, indice_pre_computado:IndexPreComputedVals , map_relevantes:Mapping[str,Set[int]], cleaner: Cleaner):
		"""
			Para um daterminada consulta `query` é extraído do indice `index` os documentos mais relevantes, considerando 
			um modelo informado pelo usuário. O `indice_pre_computado` possui valores précalculados que auxiliarão na tarefa. 
			Além disso, para algumas consultas, é impresso a precisão e revocação nos top 5, 10, 20 e 50. Essas consultas estão
			Especificadas em `map_relevantes` em que a chave é a consulta e o valor é o conjunto de ids de documentos relevantes
			para esta consulta.
		"""
		time_checker = CheckTime()

		#PEça para usuario selecionar entre Booleano ou modelo vetorial para intanciar o QueryRunner
		#apropriadamente. NO caso do booleano, vc deve pedir ao usuario se será um "and" ou "or" entre os termos.
		#abaixo, existem exemplos fixos.
		model = "Modelo "
		qr = None
		which_model = input("Digite: b -> Booleano, v -> Vetorial")
		if which_model == 'b':
			model = model + "Booleano "
			which_operation = input("Digite: o -> Or, a -> And")
			if which_operation == 'o':
				model = model + "OR"
				qr = QueryRunner(BooleanRankingModel(OPERATOR.AND), indice, cleaner)
			else:
				model = model + "AND"
				qr = qr = QueryRunner(BooleanRankingModel(OPERATOR.AND), indice, cleaner)
		else:
			model = model + "Vetorial"
			qr = QueryRunner(VectorRankingModel(indice_pre_computado), indice, cleaner)
		print(f"\n{model}")
		time_checker.print_delta("Query Creation")

		query = cleaner.preprocess_text(query)
		_query = query.replace(" ", "_")

		#Utilize o método get_docs_term para obter a lista de documentos que responde esta consulta
		docs_term = qr.get_docs_term(query)
		respostas = list(docs_term[0])
		time_checker.print_delta(f"anwered with {len(respostas)} docs")

		#nesse if, vc irá verificar se o termo possui documentos relevantes associados a ele
		#se possuir, vc deverá calcular a Precisao e revocação nos top 5, 10, 20, 50.
		#O for que fiz abaixo é só uma sugestao e o metododo countTopNRelevants podera auxiliar no calculo da revocacao e precisao
		precision = []
		recall = []

		# print(f"_query: {_query}")
		# print(f"map_relevantes: {map_relevantes}")

		if(True and _query in map_relevantes.keys()):
			doc_relevantes = map_relevantes[_query]
			arr_top = [5,10,20,50]
			revocacao = 0
			precisao = 0
			for n in arr_top:
				# revocacao = 0#substitua aqui pelo calculo da revocacao topN
				# precisao = 0#substitua aqui pelo calculo da revocacao topN
				precisao, revocacao = qr.compute_precision_recall(n, respostas, doc_relevantes)
				
				precision.append(precisao)
				recall.append(revocacao)
				
				print(f"Precisao @{n}: {precisao} && Recall @{n}: {revocacao}")

		#imprima aas top 10 respostas
		top_answers = respostas[:10]

		return top_answers, (precision, recall)

	@staticmethod
	def main():
		#leia o indice (base da dados fornecida)
		index = Index().read("wiki_hash.idx")

		dict_docs_title = {}
		with open("titlePerDoc.dat", encoding="utf8") as arq:
			for l in arq:
				l = l.split(";")
				dict_docs_title[int(l[0])] = l[1].strip()

		#Instancie o IndicePreCompModelo para pr ecomputar os valores necessarios para a query
		print("Precomputando valores atraves do indice...")
		check_time = CheckTime()
		
		indexPreCom = IndexPreComputedVals(index)

		check_time.print_delta("Precomputou valores")

		#encontra os docs relevantes
		print("encontra os docs relevantes...")
		map_relevance = QueryRunner.get_relevance_per_query()
		
		#aquui, peça para o usuário uma query (voce pode deixar isso num while ou fazer um interface grafica se estiver bastante animado ;)
		n=1
		while True:
			what_user_want = input("Digite: p -> pesquisa, s -> sair")
			if what_user_want == 'p':
				query = input("Digite a query: ")
				cl = Cleaner(
						stop_words_file="stopwords.txt",language="portuguese",
						perform_stop_words_removal=True,perform_accents_removal=True,
						perform_stemming=False
					)
				print(f"\n_____________Pesquisa {n}_____________")
				print("Fazendo query...")
				answers = QueryRunner.runQuery(query, index, indexPreCom, map_relevance, cl)
				for doc in answers[0]:
					print(f"{doc}: {dict_docs_title[doc]}")
				n=n+1
				
			else:
				print(f"\nAdeus")
				break

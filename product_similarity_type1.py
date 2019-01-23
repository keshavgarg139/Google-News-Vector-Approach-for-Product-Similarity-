from importlib import reload
import mysql.connector
import time
import csv
import gensim
from statistics import mean
from nltk.corpus import stopwords
import sys
import numpy
import math
import re
reload(sys)

def remove_special_chars(text):
	final = [re.sub(r"[^a-zA-Z0-9]+", ' ', k) for k in text.split("\n")]
	return " ".join(final)

def remove_stop_and_split(sentence):
	stop = list(stopwords.words('english'))
	sent_split = list(y for y in sentence.split() if y not in stop)
	return sent_split

def find_similar(required_topn, search_ids = ['N10987271A']):

	print("\n.....Please wait while the model is being loaded..... \n")
	start = time.time()
	word_vectors = gensim.models.KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin.gz', binary=True)
	print("Model is loaded in time = ",time.time()-start)

	connection = mysql.connector.connect(host='127.0.0.1',port=3341,database='wecat',user='developer',password='')
    db_Info = connection.get_server_info()
    print("Connected to MySQL database... MySQL Server version on ",db_Info)
    cursor = connection.cursor()

    similar_products = []

    print('\required_topn recieved by function are - ',required_topn,'\n')
    print('\ntype of required_topn recieved by function are - ',type(required_topn),'\n')

	for search_id in search_ids:

		print('\n id_product inside the core function is = ',search_id,'\n' )
        print('type of id_product is = ',type(search_id))  

        cmmd = "select id_product, product_title, attribute_key_1,attribute_value_1,attribute_key_2,attribute_value_2,attribute_key_3,attribute_value_3,attribute_key_4,attribute_value_4,attribute_key_5,attribute_value_5,feature_bullet_1,feature_bullet_2,feature_bullet_3,feature_bullet_4,feature_bullet_5,long_description from product_text_en where id_product in (select id_product from product where id_product_subtype = (select id_product_subtype from product where id_product = '{}') and id_product <> '{}' )".format(search_id,search_id)
        query = "select id_product, product_title, attribute_key_1,attribute_value_1,attribute_key_2,attribute_value_2,attribute_key_3,attribute_value_3,attribute_key_4,attribute_value_4,attribute_key_5,attribute_value_5,feature_bullet_1,feature_bullet_2,feature_bullet_3,feature_bullet_4,feature_bullet_5,long_description from product_text_en where id_product='%s'"%search_id

        metric_cmmd = "select id_product, product_length, product_height, product_width_depth from product_metric where id_product in (select id_product from product where id_product_subtype = (select id_product_subtype from product where id_product='{}') and id_product<>'{}')".format(search_id,search_id)
        query_metric = "select id_product, product_length, product_height, product_width_depth from product_metric where id_product = '%s'"%search_id

        brand_cmmd = "select id_product, id_brand from product where id_product in (select id_product from product where id_product_subtype = (select id_product_subtype from product where id_product='{}') and id_product<>'{}')".format(search_id,search_id)
        brand_query = "select id_product, id_brand from product where id_product = '%s' "%search_id

		cursor.execute(query)
		data = cursor.fetchall()
		query_data=[]
		x = ' '.join(str(y) for y in data[0][2:] if y is not None )
		x = remove_special_chars(x)
		query_title = remove_special_chars(data[0][1])
		query_data.append(data[0][0])
		query_data.append(data[0][1])
		query_data.append(x)
		query_desc_split = remove_stop_and_split(x)
		query_title_split = remove_stop_and_split(query_title)

		cursor.execute(query_metric)
		metric_query = cursor.fetchall()[0][1:]
		metric_query_none_indices = list(i for i,x in enumerate(metric_query) if x is None)

		cursor.execute(metric_cmmd)
		metrics_data = cursor.fetchall()

		data2=[]
		headers = ["sno", "id_product", "product_title", "description", "title_similarity", "desc_similarity","metrics_similarity", "brand_similarity", "total_similarity"]
		data2.append(headers)
		query_row_csv = ['Query', data[0][0], data[0][1], x, 1, 1, 1, 1, 1]
		data2.append(query_row_csv)

		cursor.execute(cmmd)
		data = cursor.fetchall()
		cursor.execute(brand_cmmd)
		brand_cmmd_data = cursor.fetchall()
		cursor.execute(brand_query)
		query_brand = cursor.fetchall()[0][1]

		topn = required_topn
		print("topn = ", topn)
		if len(data) < topn:
			topn = len(data)
		print("topn = ", topn)

		for i,row in enumerate(data):

			new_row=[]

			if row[1] is not None:
				new_row.append(i)
				new_row.append(row[0])
				new_row.append(row[1])
				title_split = remove_stop_and_split(row[1])
				wmd_title = word_vectors.wmdistance(query_title_split, title_split)  # title's wmd
				title_wmd_sim = 1 / (1 + wmd_title)  # converting distance(dissimilarity) -> similarity
			else :
				continue

			desc = ' '.join(str(y) for y in row[2:] if y is not None )
			desc = remove_special_chars(desc)
			if desc is not '' :
				desc_split = remove_stop_and_split(desc)
				wmd_desc = word_vectors.wmdistance(query_desc_split, desc_split)  # description's wmd
				desc_wmd_sim = 1 / (1 + wmd_desc)  # converting distance(dissimilarity) -> similarity
			else:
				desc_wmd_sim = 0

			new_row.append(desc)

			metrics1 = list(float(x) if x is not None else x for x in metric_query )
			metrics2 = list(float(x) if x is not None else x for x in metrics_data[i][1:] )
			flag = 1
			for i in range(len(metrics1)):
				if type(metrics1[i]) != type(metrics2[i]):
					sim_metrics = 0
					flag = 0
					break
			if flag:
				metrics1 = list(float(0) if x is None else float(x) for x in metrics1)
				metrics2 = list(float(0) if x is None else float(x) for x in metrics2)
				if numpy.linalg.norm(metrics1) == 0 or numpy.linalg.norm(metrics2) == 0 :
					sim_metrics = 0
				else:
					sim_metrics = numpy.dot(metrics1, metrics2) / (numpy.linalg.norm(metrics1) * numpy.linalg.norm(metrics2))
					sim_metrics = 0 if math.isnan(sim_metrics) else sim_metrics

			brand_sim = 1 if brand_cmmd_data[i][1] == query_brand else 0

			new_row.append(desc_wmd_sim)
			new_row.append(title_wmd_sim)
			new_row.append(sim_metrics)
			new_row.append(brand_sim)

			all_sims = list(float(x) for x in new_row[4:] if x!=0 )
			total_sim = mean(all_sims)
			new_row.append(total_sim)

			data2.append(new_row)

		data2[2:] = sorted(data2[2:], key=lambda x: x[8], reverse=True)

		top20 = data2[:topn+3]

		similar_products.append(top)
		# file = '%s.csv'%search_id
		# with open( file, 'w') as out:
		# 	writer = csv.writer(out)
		# 	for row in top20:
		# 		writer.writerow(row)

	if(connection.is_connected()):
		cursor.close()
		connection.close()
		print("MySQL connection is closed")

	return similar_products	

def main():

    search_ids = ['N10987282A', 'N10987659A']
    prods = find_similar(20,search_ids)
    for i in prods:
        print(len(i))

if __name__== "__main__":
	main()
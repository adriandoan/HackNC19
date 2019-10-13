# -*- coding: utf-8 -*-
"""
Created on Sat Oct 12 21:15:00 2019

@author: Eli
"""

# -*- coding: utf-8 -*-
"""
Created on Sat Oct 12 14:07:07 2019

@author: Eli

df = data frame with all of the information
"""


print("Importing dependencies...")
import numpy as np
import re
import pandas as pd
import json
import gzip
from sqlitedict import SqliteDict

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize
nltk.download('stopwords')
nltk.download('punkt')

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

print("Loading data...")

helpMe = {}

df = pd.read_csv (r'C:\Users\Eli\Desktop\HACK_NC\data.csv')
pd.set_option('display.max_colwidth', -1)

#set up variables
num_paragraphs, num_pics, text, num_words, num_chars, num_tags, abv75p, abv50p, abv25p, bottom25p = [],[],[],[],[],[],[],[],[],[]

#used for ML
df1 = df[df.columns[-23:]]

#used to calculate what percentile by hits an article is in
p75 = np.percentile(df['Hits'], 75)
p50 = np.percentile(df['Hits'], 50)
p25 = np.percentile(df['Hits'], 25)

for row in df.itertuples():
    i = 0
    for x in row[12:]:
        if x:
            i += 1
    num_tags.append(i)
    
    num_paragraphs.append(len(re.findall(r"<br><br>", row.Body)))
    num_pics.append(len(re.findall(r"href=", row.Body)))
    text.append(re.sub(r'<[^<>]+>', '', row.Body))
    num_words.append(len(text[-1].split()))
    num_chars.append(len(text[-1]))
    
    bottom25p.append(int(row.Hits <= p25))
    abv25p.append(int(row.Hits > p25 and row.Hits <= p50))
    abv50p.append(int(row.Hits > p50 and row.Hits <= p75))
    abv75p.append(int(row.Hits > p75))

df = df.assign(num_paragraphs=num_paragraphs)
df = df.assign(num_pics=num_pics)
df = df.assign(text=text)
df = df.assign(num_words=num_words)
df = df.assign(num_chars=num_chars)
df = df.assign(num_tags=num_tags)
df = df.assign(abv75p=abv75p)
df = df.assign(abv50p=abv50p)
df = df.assign(abv25p=abv25p)
df = df.assign(bottom25p=bottom25p)

# Neural Net One: Multi Label
df1.insert(0, "text", text)
df1 = df1.assign(abv75p=abv75p)
df1 = df1.assign(abv50p=abv50p)
df1 = df1.assign(abv25p=abv25p)
df1 = df1.assign(bottom25p=bottom25p)



def analyzeText(df1, usersText):
    
    #CLEANING THE TEXT ========================================================
    def removePunct(text):
        tokens = word_tokenize(text)
        words = [word for word in tokens if word.isalpha()]
        return " ".join(words)
    
    def stemText(text):
        stemmer = SnowballStemmer("english")
        return ' '.join(stemmer.stem(word) for word in text.split())
    
    #apply text cleaning methods
    df1['text'] = df1['text'].str.lower().apply(removePunct).apply(stemText)
    
    #SETTING UP THE MODEL =====================================================
    train, test = train_test_split(df1, test_size=0.33, shuffle=True)
    X_train = train.text
    X_test = test.text
    
    stop_words = set(stopwords.words('english'))
    
    SVC_pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(stop_words=stop_words)),
                ('clf', OneVsRestClassifier(LinearSVC(), n_jobs=1)),
            ])
        
    tags = np.array((df1.columns.values)[1:])
    
    #TRAINING AND PERDICTING WITH THE MODEL ===================================
    myInput = [usersText]
    prdictTags = []
    prdictPrcnt = []
    tagsAcc = 0
    prcntAcc = 0
    totalAcc = 0
    i = 0
    
    for tag in tags:
        print('... Processing {}'.format(tag))
       
        #train the model using X_dtm & y
        SVC_pipeline.fit(X_train, train[tag])
        
        #compute the testing accuracy
        prediction = SVC_pipeline.predict(X_test)
        print('Test accuracy is {}'.format(accuracy_score(test[tag], prediction)))
        acc = accuracy_score(test[tag], prediction)
        
        #calculate overall accuracy
        totalAcc += acc 
        i += 1
        if i == 23:
            totalAcc = totalAcc / 24
            tagsAcc = totalAcc
            print("\n")
            print('Overall average test accuracy for tag predictions is {}'.format(totalAcc))
            totalAcc = 0
        if i == 27:
            totalAcc = totalAcc / 4
            prcntAcc = totalAcc
            print("\n")
            print('Overall average test accuracy for hit percentile predictions is {}'.format(totalAcc))
        
        #perdict the hit percentile and tags for the input article 
        if i <= 23:
            if SVC_pipeline.predict(myInput)[0]:
                prdictTags.append(tag)
        else:
            if SVC_pipeline.predict(myInput)[0]:
                prdictPrcnt.append(tag)        
        
    if (prdictPrcnt):
        if (prdictPrcnt[0] == "abv75p"):
            prcntString = "is fire! In terms of hits, it should rank in the top 25% of articles!"
            suggestedWords = "With writing like that, you don't need any word suggestions." 
        if (prdictPrcnt[0] == "abv50p"):
            prcntString = "is pretty good! In terms of hits, it should rank in the top 50% of articles!"
        if (prdictPrcnt[0] == "abv25p"):
            prcntString = "is may need a rewrite. In terms of hits, it will likely rank in the bottom 50% of articles."
        if (prdictPrcnt[0] == "bottom25p"):
            prcntString = "is in trouble. In terms of hits, it will likely rank in the bottom 25% of articles."
       
    #CALCULATE SUGGESTIONS ====================================================
    suggestedWords, prcntString, similarArticle = "", "", ""
    
    #get articles with the same tags
    if (len(prdictTags) == 0):
        articlesWSameTags = df1
        for tag in prdictTags:
            articlesWSameTags = articlesWSameTags[articlesWSameTags[tag] == 1]
        articlesWSameTags = articlesWSameTags[articlesWSameTags['abv75p'] == 1]
    else:
        articlesWSameTags = []
        
    #articlesWSameTags['text'] = articlesWSameTags['text'].apply(lambda x: ' '.join([word for word in x.split() if word not in (stop_words)]))
    
    if (len(articlesWSameTags) == 0):
        #suggestedWords = "Based on high-scoring articles that are similar to yours, we suggest you spice up your writing by adding these words: " + suggestedWords
        similarArticle = "If you are interested in further reading, here is a high-scoring article that is similar to yours: " + articlesWSameTags[0]
    else: 
        suggestedWords = "There are not enough similar articles to suggest words."
        similarArticle = "There are not enough similar articles to suggest similar articles."
        
    if (len(suggestedWords) <= 0):
        suggestedWords = "To improve your article, consiter adding these words: " #how to get this?????????????????????????????
    
    myDict = {
            'tag list':prdictTags,
            'percents':prdictPrcnt,
            'percentile acc': prcntAcc,
            'tag acc': tagsAcc,
            'similars': articlesWSameTags
            }
    #output = []
    #output.append("We can say with " + str(prdictTags) + "% certainty that you should be using these tags:" + str(prdictTags))
    #output.append("We can also say with " + str(prdictPrcnt) + "% certainty that your article" + prcntString)
    #output.append(suggestedWords)
    #output.append(similarArticle)
    
    return myDict

out = analyzeText(df1, "article")

#!/usr/bin/env python3
import pandas as pd
from retriever.retriever_sklearn import TfidfRetriever
from retriever.filters import filter_paragraphs
from ast import literal_eval

def search(query, df):
    df = filter_paragraphs(df)
    retriever = TfidfRetriever(ngram_range=(1, 2), min_df=0, max_df=10, stop_words='english')
    retriever.fit(df)
    best_indexes = list(retriever.predict(query).keys())
    return list(df.iloc[inx] for inx in best_indexes)

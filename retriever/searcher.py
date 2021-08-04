#!/usr/bin/env python3
import pandas as pd
from retriever.retriever_sklearn import TfidfRetriever

def search(query, df):
    retriever = TfidfRetriever(ngram_range=(1, 2), min_df=0, max_df=10, stop_words='english')
    df = retriever.filter_pages(df)
    retriever.fit(df)
    best = retriever.predict(query)
    best_indexes = list(best.keys())
    best_scores = list(best.values())
    return best_scores, list(df.iloc[inx] for inx in best_indexes)

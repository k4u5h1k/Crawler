#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np

def filter_paragraphs(
    articles,
    drop_empty=True,
    read_threshold=1000,
    public_data=True,
    min_length=0,
    max_length=5000,
):
    """
    Cleans the pages and filters them regarding their length
    Parameters
    ----------
    articles : DataFrame of all the articles 
    Returns
    -------
    Cleaned and filtered dataframe
    Examples
    --------
    >>> import pandas as pd
    >>> from cdqa.utils.filters import filter_pages
    >>> df = pd.read_csv('data.csv')
    >>> df_cleaned = filter_pages(df)
    """

    # Replace and split
    def replace_and_split(pages):
        for page in pages:
            page.replace("'s", " " "s").replace("\\n", "").split("'")
        return pages

    # Select pages with the required size
    def filter_on_size(pages, min_length=min_length, max_length=max_length):
        page_filtered = [
            page.strip()[:max_length]
            for page in pages
        ]
        return page_filtered

    # Cleaning and filtering
    articles["pages"] = articles["pages"].apply(replace_and_split)
    articles["pages"] = articles["pages"].apply(filter_on_size)
    articles["pages"] = articles["pages"].apply(
        lambda x: x if len(x) > 0 else np.nan
    )

    # Read threshold for private dataset
    if not public_data:
        articles = articles.loc[articles["number_of_read"] >= read_threshold]

    # Drop empty articles
    if drop_empty:
        articles = articles.dropna(subset=["pages"]).reset_index(drop=True)

    return articles


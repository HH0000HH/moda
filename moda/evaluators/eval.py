import math

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from moda.evaluators.metrics.metrics import _initialize_metrics, get_final_metrics, get_metrics_with_shift


def eval_models(X, y, models, label_col_name='label', prediction_col_name='prediction', value_col_name='value',
                verbose=False, window_size_for_metrics=3, train_percent=70):
    """Evalutes one or more modeling with the provided datasets

     Parameters
     ----------
     X : pandas.DataFrame
         A pandas DataFrame with a two-leveled multi-index, the first
            indexing time and the second indexing class/topic frequency
            per-window, and a single column of a numeric dtype, giving said
            frequency.
    y : pandas.DataFrame
        A pandas DataFrame with a two-leveled multi-index, the first
            indexing time and the second indexing class/topic frequency
            per-window, and a single column of a integer type (-1,0,1), with the ground truth labels for each time and class/topic
    modeling : list of Scikit learn style modeling (fit-predict). These modeling will be evaluated
    label_col_name : The name of the column holding the labeled data
    prediction_col_name : The name of the column generated by the model for prediction
    value_col_name : The name of the column holding the time series values
    n_splits : integer
        The number of splits for TimeSeriesSplit. see  http://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

    Returns
    -------
    res : a dictionary of metrics per model
    """

    if X is None:
        raise TypeError
    if y is None:
        raise TypeError

    per_model_res = {}
    datetimeindex = X.index.levels[0]
    num_dates = len(datetimeindex)

    train = datetimeindex[:int(num_dates * train_percent / 100)]
    test = datetimeindex[int(num_dates * train_percent / 100):]
    categories = X.index.levels[1]

    for model in models:
        counter = 0
        metrics = _initialize_metrics(categories)

        if verbose:
            print("Model: {}".format(str(model)))
        all_iterations_res = []

        train_samples = _prep_set(X, train)
        train_labels = _prep_set(y, train)

        test_samples = _prep_set(X, test)
        test_labels = _prep_set(y, test)

        if (test_labels is not None) and (len(test_labels) > 0):
            # run the model
            print('Fitting...')
            model.fit(X=train_samples, y=train_labels)
            print('Predicting...')
            prediction = model.predict(X=test_samples)

            # evaluate results, aggregate metrics
            metrics = get_evaluation_metrics(test_samples, prediction, test_labels, metrics,
                                             value_col_name=value_col_name, label_col_name=label_col_name,
                                             prediction_col_name=prediction_col_name,
                                             window_size_for_metrics=window_size_for_metrics)

            counter += 1

        final_metrics = get_final_metrics(metrics)
        if verbose:
            print(final_metrics)
        per_model_res[str(model.__name__)] = final_metrics
    return per_model_res


def eval_models_CV(X, y, models, label_col_name='label', prediction_col_name='prediction', value_col_name='value',
                   n_splits=None, verbose=True, window_size_for_metrics=3):
    """Evalutes one or more modeling with the provided datasets, using time series cross validation

     Parameters
     ----------
     X : pandas.DataFrame
         A pandas DataFrame with a two-leveled multi-index, the first
            indexing time and the second indexing class/topic frequency
            per-window, and a single column of a numeric dtype, giving said
            frequency.
    y : pandas.DataFrame
        A pandas DataFrame with a two-leveled multi-index, the first
            indexing time and the second indexing class/topic frequency
            per-window, and a single column of a integer type (-1,0,1), with the ground truth labels for each time and class/topic
    modeling : list of Scikit learn style modeling (fit-predict). These modeling will be evaluated
    label_col_name : The name of the column holding the labeled data
    prediction_col_name : The name of the column generated by the model for prediction
    value_col_name : The name of the column holding the time series values
    n_splits : integer
        The number of splits for TimeSeriesSplit. see  http://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

    Returns
    -------
    res : a dictionary of metrics per model
    """

    if X is None:
        raise TypeError
    if y is None:
        raise TypeError

    if n_splits is None:
        n_splits = int(len(X.index.levels[0]) / 2)
        print("Running {} splits".format(n_splits))

    if n_splits > len(X.index.levels[0]):
        n_splits = int(len(X.index.levels[0]) / 2)
        print("Warning: n_splits cannot be larger than the number of dates. Reducing n_splits to {}".format(n_splits))

    per_model_res = {}

    datetimeindex = X.index.levels[0]
    categories = X.index.levels[1]
    for model in models:
        counter = 0
        metrics = _initialize_metrics(categories)

        tscv = TimeSeriesSplit(n_splits=n_splits)
        if verbose:
            print("Model: {}".format(str(model)))
        all_iterations_res = []
        for train, test in tscv.split(datetimeindex):
            if verbose:
                print("Iteration: %s, Train size: %s, Test size: %s, Data size: %s " % (
                    counter, len(train), len(test), len(datetimeindex)))

            train_samples = _prep_set(X, datetimeindex[train])
            train_labels = _prep_set(y, datetimeindex[train])

            test_samples = _prep_set(X, datetimeindex[test])
            test_labels = _prep_set(y, datetimeindex[test])

            if (test_labels is not None) and (len(test_labels) > 0):
                # run the model
                model.fit(X=train_samples, y=train_labels)
                prediction = model.predict(X=test_samples)

                # evaluate results, aggregate metrics
                metrics = get_evaluation_metrics(test_samples, prediction, test_labels, metrics,
                                                 value_col_name=value_col_name, label_col_name=label_col_name,
                                                 prediction_col_name=prediction_col_name,
                                                 window_size_for_metrics=window_size_for_metrics)

                counter += 1

        final_metrics = get_final_metrics(metrics)
        if verbose:
            print(final_metrics)
        per_model_res[str(model.__name__)] = final_metrics
    return per_model_res


def _prep_set(X, dates):
    new_samples = X.copy().loc[dates]
    new_samples.index = new_samples.index.remove_unused_levels()
    return new_samples




def get_evaluation_metrics(test_values_df, prediction_df, labels_df, metrics=None, value_col_name='value',
                           label_col_name='label', prediction_col_name='prediction', window_size_for_metrics=5):
    """
    Evalutes a model with a specific set of metrics,
    :param label_col_name: The name of the label column in the testing data
    :param metrics: A dictionary of metric names and current values (i.e. {'TP': 0, 'FP': 0, 'TN': 0, 'FN': 0, 'num_samples': 0, 'num_values': 0})
    :param model: A model to be run, which has a fit and predict methods.
    :param prediction_col_name:
    :param test_labels: The test set's labels Series
    :param test_samples: The test set
    :param train_labels: The training set's labels Series
    :param train_samples: The training set
    :param value_col_name: The name of the Series with the actual time series values
    :param verbose:
    """

    if metrics is None:
        metrics = {}
        categories = prediction_df.index.levels[1]
        _initialize_metrics(categories)

    # join the model results and test set, assuming that some dates or times are missing
    results = _join_pred_to_dataset(labels_df, prediction_df, test_values_df, label_col_name, value_col_name)
    # print(results)
    for category in results.index.levels[1]:
        metrics = get_metrics_for_one_category(results, label_col_name, prediction_col_name,
                                               value_col_name, window_size_for_metrics, category, metrics)

    return metrics


def get_metrics_for_one_category(dataset, label_col_name, prediction_col_name, value_col_name,
                                 window_size_for_metrics, category="", metrics=None):
    """
    Returns metrics for a specific category in the data.
    :param dataset: A dataset holding the prediction, actual and value columns.
    :param label_col_name: The name of the actual values (labeled) Series
    :param prediction_col_name: The name of the predicted values Series
    :param value_col_name: Name of the value column in the dataset
    :param window_size_for_metrics:  The allowed shift to the left or the right.
    a window_size of 2 means that the corresponding value will be looked for
    in 2 cells to the left and two cells to the right
    :param category: (Optional) The name of the category if the dataset holds multiple categories
    :param metrics: A dictionary of TP, FP and FN per category

    :return: a dictionary with the precision, recall, f1, f0.5 metrics,
    as well as the number of samples per category and the sum of values.
    """
    category_results = dataset.loc[pd.IndexSlice[:, category], :]
    category_results.index = category_results.index.remove_unused_levels()
    # Calculate TP, FP and FN
    metrics = get_metrics_with_shift(predicted=category_results[prediction_col_name].values,
                                     actual=category_results[label_col_name].values,
                                     category=category,
                                     metrics=metrics,
                                     window_size=window_size_for_metrics)
    # Calculate additional accumulators
    metrics[category]['num_samples'] += len(category_results)
    metrics[category]['num_values'] += np.sum(category_results[value_col_name])
    return metrics


def _join_pred_to_dataset(original_df, prediction_df, test_values_df, label_col_name, value_col_name):
    results = pd.merge(prediction_df, original_df, how='left', on=['date', 'category'])[['prediction',label_col_name]]
    results = pd.merge(results, test_values_df, how='left', on=['date', 'category'])
    results[label_col_name] = results[label_col_name].fillna(0)
    results.sort_index(level=['date', 'category'], ascending=True, inplace=True)
    return results


# coding=utf-8
# Copyright 2022 The Uncertainty Baselines Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for colab_utils."""

from absl.testing import absltest
from absl.testing import parameterized

import numpy as np
import pandas as pd
import colab_utils  # local file import from experimental.big_paper


def get_test_untuned_dataframe():
  # Experiment where we sweep `config.lr` over [.01, .02].
  # - config.lr = .01 has better validation loss
  # - config.lr = .02 has better AUROC.
  rows = [
      {
          'config.seed': 1,
          'config.lr': .01,
          'config.steps': 500,
          'val_loss': .1,
          'msp_auroc': .8,
      },
      {
          'config.seed': 2,
          'config.lr': .01,
          'config.steps': 500,
          'val_loss': .08,
          'msp_auroc': .6
      },
      {
          'config.seed': 1,
          'config.lr': .02,
          'config.steps': 500,
          'val_loss': .5,
          'msp_auroc': .9
      },
      {
          'config.seed': 2,
          'config.lr': .02,
          'config.steps': 500,
          'val_loss': .8,
          'msp_auroc': .95
      },
  ]
  df = pd.DataFrame(rows)
  df['model'] = 'Det'
  df['config.dataset'] = 'Cifar10'
  return df


def get_test_tuned_dataset():
  det_rows = [{
      'model': 'Det',
      'config.dataset': 'jft/entity:1.0.0',
      'exaflops': 100,
      'z/cars_5shot': .6,
      'val_loss': .3,
  }, {
      'model': 'Det',
      'config.dataset': 'jft/entity:1.0.0',
      'exaflops': 150,
      'z/cars_5shot': .8,
      'val_loss': .5,
  }, {
      'model': 'Det',
      'config.dataset': 'cifar10',
      'cifar_10h_ece': .1,
      'test_loss': .2,
  }]

  be_rows = [{
      'model': 'BE',
      'config.dataset': 'imagenet21k',
      'exaflops': 200,
      'z/cars_5shot': .9,
      'val_loss': .3
  }, {
      'model': 'BE',
      'config.dataset': 'cifar10',
      'cifar_10h_ece': .02,
      'test_loss': .01,
  }]
  return pd.DataFrame(det_rows + be_rows)


class ColabUtilsTest(parameterized.TestCase):

  @parameterized.named_parameters(
      dict(
          testcase_name='_numerical_column',
          df=pd.DataFrame({
              'a': [2, 2, 2],
              'b': ['x', 'y', 'z']
          }),
          column='a',
          expected_value=2),
      dict(
          testcase_name='_single_row',
          df=pd.DataFrame({
              'a': [2,],
              'b': ['x']
          }),
          column='a',
          expected_value=2),
      dict(
          testcase_name='_text_column',
          df=pd.DataFrame({
              'a': [2, 3, 4],
              'b': ['z', 'z', 'z']
          }),
          column='b',
          expected_value='z'),
  )
  def test_get_unique_value(self, df, column, expected_value):
    self.assertEqual(colab_utils.get_unique_value(df, column), expected_value)

  @parameterized.named_parameters(
      dict(
          testcase_name='_empty_dataframe',
          df=pd.DataFrame({
              'a': [],
              'b': []
          }),
          column='a'),
      dict(
          testcase_name='_non_unique_values',
          df=pd.DataFrame({
              'a': [2, 2, 2],
              'b': ['x', 'y', 'z']
          }),
          column='b'),
  )
  def test_get_unique_value_fails(self, df, column):
    with self.assertRaisesRegex(ValueError,
                                'Expected unique value in column'):
      colab_utils.get_unique_value(df, column)

  @parameterized.named_parameters(
      dict(
          testcase_name='_no_nans',
          df=pd.DataFrame({
              'a': [2, 2, np.nan, np.nan],
              'b': [np.nan, np.nan, 'x', np.nan],
              'c': [np.nan, np.nan, np.nan, 'y']
          }),
          expected_series=pd.Series([2, 2, 'x', 'y'], name='a'),
      ),
      dict(
          testcase_name='_with_nans',
          df=pd.DataFrame({
              'a': [2, np.nan, 3, np.nan],
              'b': [np.nan, np.nan, np.nan, 'x']
          }),
          expected_series=pd.Series([2, np.nan, 3, 'x'], name='a')),
  )
  def test_row_wise_unique_non_nan(self, df, expected_series):
    pd.testing.assert_series_equal(
        colab_utils.row_wise_unique_non_nan(df), expected_series)

  def test_row_wise_unique_non_nan_fails(self):
    df = pd.DataFrame({'a': [1, 2, np.nan], 'b': [1, np.nan, 3]})
    with self.assertRaisesRegex(ValueError, 'have multiple set values'):
      colab_utils.row_wise_unique_non_nan(df)

  @parameterized.parameters(('config.seed', (), True),
                            ('learning_rate', (), False),
                            ('learning_rate', ('learning_rate', 'model'), True),
                            ('random_seed', (), False))
  def test_is_hyperparameter(self, column, auxiliary_hparams, expected_result):
    self.assertEqual(
        colab_utils.is_hyperparameter(column, auxiliary_hparams),
        expected_result)

  @parameterized.parameters(
      ((), ['config.seed', 'config.lr']),
      (('config.seed'), ['config.lr']),
      (('config.seed', 'config.lr'), []),
  )
  def test_get_sweeped_hyperparameters(self, marginalization_hparams,
                                       expected_sweeped_params):
    df = get_test_untuned_dataframe()
    actual_sweeped_hparams = colab_utils.get_sweeped_hyperparameters(
        df, marginalization_hparams)
    self.assertSetEqual(
        set(actual_sweeped_hparams), set(expected_sweeped_params))

  @parameterized.named_parameters(
      dict(
          testcase_name='_tune_lr_on_loss',
          metric='val_loss',
          marginalization_hparams=('config.seed',),
          expected_hparams={'config.lr': .01},
      ),
      dict(
          testcase_name='_tune_lr_on_auroc',
          metric='msp_auroc',
          marginalization_hparams=('config.seed',),
          expected_hparams={'config.lr': .02},
      ),
      dict(
          testcase_name='_tune_lr_and_seed_on_loss',
          metric='val_loss',
          marginalization_hparams=(),
          expected_hparams={
              'config.lr': .01,
              'config.seed': 2
          },
      ),
      dict(
          testcase_name='_no_tuning',
          metric='val_loss',
          marginalization_hparams=('config.lr', 'config.seed'),
          expected_hparams={},
      ),
  )
  def test_get_best_hyperparameters(self, metric, marginalization_hparams,
                                    expected_hparams):
    df = get_test_untuned_dataframe()
    actual_hparams = colab_utils.get_best_hyperparameters(
        df, metric, marginalization_hparams)
    self.assertDictEqual(actual_hparams, expected_hparams)

  @parameterized.parameters(('val_loss', .01), ('msp_auroc', .02))
  def test_get_tuned_results(self, tuning_metric, best_lr):
    df = get_test_untuned_dataframe()
    actual_results = colab_utils.get_tuned_results(
        df, tuning_metric=tuning_metric)
    expected_results = actual_results[actual_results['config.lr'] == best_lr]
    pd.testing.assert_frame_equal(actual_results, expected_results)

  def test_fill_upstream_test_metrics(self):
    input_df = pd.DataFrame({
        'config.dataset': ['jft/entity:1.0.0', 'cifar10', 'imagenet21k'],
        'val_loss': [.1, .2, .3],
        'val_prec@1': [.9, .8, .4],
        'val_ece': [.2, .5, .8],
        'val_calib_auc': [.2, .5, .8],
        'test_loss': [np.nan, .9, np.nan],
        'test_prec@1': [.2, .1, np.nan]  # First value should be overwritten.
    })
    expected_df = pd.DataFrame({
        'config.dataset': ['jft/entity:1.0.0', 'cifar10', 'imagenet21k'],
        'val_loss': [.1, .2, .3],
        'val_prec@1': [.9, .8, .4],
        'val_ece': [.2, .5, .8],
        'val_calib_auc': [.2, .5, .8],
        'test_loss': [.1, .9, .3],
        'test_prec@1': [.9, .1, .4],
        'test_ece': [.2, np.nan, .8],
        'test_calib_auc': [.2, np.nan, .8],
    })
    pd.testing.assert_frame_equal(
        colab_utils._fill_upstream_test_metrics(input_df), expected_df)

  def test_processed_tuned_results(self):
    relevant_metrics = [
        'test_loss', 'cifar_10h_ece', 'z/cars_5shot', 'exaflops'
    ]
    input_df = get_test_tuned_dataset()
    expected_be_results = {
        'model': 'BE',
        ('test_loss', 'imagenet21k'): .3,  # Filled to val_loss.
        ('test_loss', 'jft/entity:1.0.0'): np.nan,
        ('test_loss', 'cifar10'): .01,
        ('5shot_prec@1', 'few-shot cars'): .9,
        ('cifar_10h_ece', 'cifar10'): .02,
        ('exaflops', 'compute'): 200,
    }

    expected_det_results = {
        'model': 'Det',
        ('test_loss', 'jft/entity:1.0.0'): (.3 + .5) / 2,  # Filled to val_loss.
        ('test_loss', 'imagenet21k'): np.nan,
        ('test_loss', 'cifar10'): .2,
        ('cifar_10h_ece', 'cifar10'): .1,
        ('5shot_prec@1', 'few-shot cars'): (.6 + .8) / 2,
        ('exaflops', 'compute'): (100 + 150) / 2,
    }

    expected_df = pd.DataFrame([expected_be_results,
                                expected_det_results]).set_index('model')
    expected_df.columns = pd.MultiIndex.from_tuples(
        expected_df.columns, names=['metric', 'dataset'])
    result_df = colab_utils.process_tuned_results(input_df, relevant_metrics)
    pd.testing.assert_frame_equal(result_df.sort_index(axis=1),
                                  expected_df.sort_index(axis=1))

  @parameterized.parameters(
      ('ood_cifar10_msp_auroc', 'auroc'),
      ('in_domain_test/accuracy', 'accuracy'),
      ('test_prec@1', 'prec@1'),
      ('ood_test/negative_log_likelihood', 'likelihood'),
      ('ms_step', 'ms_step'),
  )
  def test_get_base_metric(self, metric_name, expected_result):
    self.assertEqual(colab_utils.get_base_metric(metric_name), expected_result)

  @parameterized.parameters('Det', 'jft/entity:1.0.0', 'cifar10_nll')
  def test_get_base_metric_fails(self, metric_name):
    with self.assertRaisesRegex(ValueError, 'Unrecognized metric'):
      colab_utils.get_base_metric(metric_name)

  @parameterized.parameters(
      ('ood_cifar10_msp_auroc', colab_utils.MetricCategory.UNCERTAINTY),
      ('in_domain_test/accuracy', colab_utils.MetricCategory.PREDICTION),
      ('ood_test/negative_log_likelihood',
       colab_utils.MetricCategory.PREDICTION),
      ('test_prec@1', colab_utils.MetricCategory.PREDICTION),
      ('5shot_prec@1', colab_utils.MetricCategory.ADAPTATION),
  )
  def test_get_metric_score_category(self, metric_name, expected_result):
    self.assertEqual(
        colab_utils.get_metric_score_category(metric_name), expected_result)

  def test_normalize_scores(self):
    entropy = np.log(10)
    input_df = pd.DataFrame({
        ('test_loss', 'cifar10'): [.2, .7],
        ('in_domain_test/ece', 'retina_country'): [.1, .3],
        ('exaflops', 'compute'): [100, 200],
    })
    input_df.columns = pd.MultiIndex.from_tuples(input_df.columns)

    expected_df = pd.DataFrame({
        ('test_loss', 'cifar10'): [1 - .2 / entropy, 1 - .7 / entropy],
        ('in_domain_test/ece', 'retina_country'): [.9, .7],
        ('exaflops', 'compute'): [100, 200],
    })
    pd.testing.assert_frame_equal(
        colab_utils._normalize_scores(input_df), expected_df)

  @parameterized.named_parameters(
      dict(
          testcase_name='_base_case',
          drop_1shot=False,
          keep_dsets=None,
          expected_df=pd.DataFrame({
              'model': ['Det', 'BE'],
              'score_prediction': [(.8 + .7) / 2, (.9 + .8) / 2],
              'score_uncertainty': [(.3 + .3) / 2, (.8 + .5) / 2],
              'score_adaptation': [(.6 + .8) / 2, (.8 + .9) / 2],
              'score': [(.8 + .7 + .3 + .3 + .6 + .8) / 6,
                        (.9 + .8 + .8 + .5 + .8 + .9) / 6],
          }),
      ),
      dict(
          testcase_name='_drop_1shot',
          drop_1shot=True,
          keep_dsets=None,
          expected_df=pd.DataFrame({
              'model': ['Det', 'BE'],
              'score_prediction': [(.8 + .7) / 2, (.9 + .8) / 2],
              'score_uncertainty': [(.3 + .3) / 2, (.8 + .5) / 2],
              'score_adaptation': [.8, .9],
              'score': [(.8 + .7 + .3 + .3 + .8) / 5,
                        (.9 + .8 + .8 + .5 + .9) / 5]
          }),
      ),
      dict(
          testcase_name='_drop_imagenet',
          drop_1shot=False,
          keep_dsets=['cifar10', 'few-shot pets'],
          expected_df=pd.DataFrame({
              'model': ['Det', 'BE'],
              'score_prediction': [.8, .9],
              'score_uncertainty': [.3, .8],
              'score_adaptation': [(.6 + .8) / 2, (.8 + .9) / 2],
              'score': [(.8 + .3 + .6 + .8) / 4, (.9 + .8 + .8 + .9) / 4],
          }),
      ),
      dict(
          testcase_name='_no_adaptation',
          drop_1shot=False,
          keep_dsets=['cifar10'],
          expected_df=pd.DataFrame({
              'model': ['Det', 'BE'],
              'score_prediction': [.8, .9],
              'score_uncertainty': [.3, .8],
              'score_adaptation': [np.nan, np.nan],
              'score': [(.8 + .3) / 2, (.9 + .8) / 2],
          }),
      )
  )
  def test_compute_score(self, drop_1shot, keep_dsets, expected_df):
    input_df = pd.DataFrame({
        'model': ['Det', 'BE'],
        ('test_prec@1', 'cifar10'): [.8, .9],  # Prediction
        ('test_prec@1', 'imagenet2012'): [.7, .8],  # Prediction
        ('ood_cifar100_msp_auroc_ece', 'cifar10'): [.7, .2],  # Uncertainty
        ('test_calib_auc', 'imagenet2012'): [.3, .5],  # Uncertainty
        ('1shot_prec@1', 'few-shot pets'): [.6, .8],  # Adaptation
        ('5shot_prec@1', 'few-shot pets'): [.8, .9],  # Adaptation
    })
    input_df.set_index('model', inplace=True)
    input_df.columns = pd.MultiIndex.from_tuples(input_df.columns)

    result_df = colab_utils.compute_score(input_df, drop_1shot, keep_dsets)
    pd.testing.assert_frame_equal(
        result_df.sort_index(axis=0).sort_index(axis=1),
        expected_df.set_index('model').sort_index(axis=0).sort_index(axis=1))


if __name__ == '__main__':
  absltest.main()

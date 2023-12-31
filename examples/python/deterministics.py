#!/usr/bin/env python

# DO NOT EDIT
# Autogenerated from the notebook deterministics.ipynb.
# Edit the notebook and then sync the output with this file.
#
# flake8: noqa
# DO NOT EDIT

# # Deterministic Terms in Time Series Models

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rc("figure", figsize=(16, 9))
plt.rc("font", size=16)

# ## Basic Use
#
# Basic configurations can be directly constructed through
# `DeterministicProcess`. These can include a constant, a time trend of any
# order, and either a seasonal or a Fourier component.
#
# The process requires an index, which is the index of the full-sample (or
# in-sample).
#
# First, we initialize a deterministic process with a constant, a linear
# time trend, and a 5-period seasonal term. The `in_sample` method returns
# the full set of values that match the index.

from statsmodels.tsa.deterministic import DeterministicProcess

index = pd.RangeIndex(0, 100)
det_proc = DeterministicProcess(index,
                                constant=True,
                                order=1,
                                seasonal=True,
                                period=5)
det_proc.in_sample()

# The `out_of_sample` returns the next `steps` values after the end of the
# in-sample.

det_proc.out_of_sample(15)

# `range(start, stop)` can also be used to produce the deterministic terms
# over any range including in- and out-of-sample.
#
# ### Notes
#
# * When the index is a pandas `DatetimeIndex` or a `PeriodIndex`, then
# `start` and `stop` can be date-like (strings, e.g., "2020-06-01", or
# Timestamp) or integers.
# * `stop` is always included in the range. While this is not very
# Pythonic, it is needed since both statsmodels and Pandas include `stop`
# when working with date-like slices.

det_proc.range(190, 210)

# ## Using a Date-like Index
#
# Next, we show the same steps using a `PeriodIndex`.

index = pd.period_range("2020-03-01", freq="M", periods=60)
det_proc = DeterministicProcess(index, constant=True, fourier=2)
det_proc.in_sample().head(12)

det_proc.out_of_sample(12)

# `range` accepts date-like arguments, which are usually given as strings.

det_proc.range("2025-01", "2026-01")

# This is equivalent to using the integer values 58 and 70.

det_proc.range(58, 70)

# ## Advanced Construction
#
# Deterministic processes with features not supported directly through the
# constructor can be created using `additional_terms` which accepts a list
# of `DetermisticTerm`. Here we create a deterministic process with two
# seasonal components: day-of-week with a 5 day period and an annual
# captured through a Fourier component with a period of 365.25 days.

from statsmodels.tsa.deterministic import Fourier, Seasonality, TimeTrend

index = pd.period_range("2020-03-01", freq="D", periods=2 * 365)
tt = TimeTrend(constant=True)
four = Fourier(period=365.25, order=2)
seas = Seasonality(period=7)
det_proc = DeterministicProcess(index, additional_terms=[tt, seas, four])
det_proc.in_sample().head(28)

# ## Custom Deterministic Terms
#
# The `DetermisticTerm` Abstract Base Class is designed to be subclassed
# to help users write custom deterministic terms.  We next show two
# examples. The first is a broken time trend that allows a break after a
# fixed number of periods. The second is a "trick" deterministic term that
# allows exogenous data, which is not really a deterministic process, to be
# treated as if was deterministic.  This lets use simplify gathering the
# terms needed for forecasting.
#
# These are intended to demonstrate the construction of custom terms. They
# can definitely be improved in terms of input validation.

from statsmodels.tsa.deterministic import DeterministicTerm


class BrokenTimeTrend(DeterministicTerm):
    def __init__(self, break_period: int):
        self._break_period = break_period

    def __str__(self):
        return "Broken Time Trend"

    def _eq_attr(self):
        return (self._break_period, )

    def in_sample(self, index: pd.Index):
        nobs = index.shape[0]
        terms = np.zeros((nobs, 2))
        terms[self._break_period:, 0] = 1
        terms[self._break_period:, 1] = np.arange(self._break_period + 1,
                                                  nobs + 1)
        return pd.DataFrame(terms,
                            columns=["const_break", "trend_break"],
                            index=index)

    def out_of_sample(self,
                      steps: int,
                      index: pd.Index,
                      forecast_index: pd.Index = None):
        # Always call extend index first
        fcast_index = self._extend_index(index, steps, forecast_index)
        nobs = index.shape[0]
        terms = np.zeros((steps, 2))
        # Assume break period is in-sample
        terms[:, 0] = 1
        terms[:, 1] = np.arange(nobs + 1, nobs + steps + 1)
        return pd.DataFrame(terms,
                            columns=["const_break", "trend_break"],
                            index=fcast_index)


btt = BrokenTimeTrend(60)
tt = TimeTrend(constant=True, order=1)
index = pd.RangeIndex(100)
det_proc = DeterministicProcess(index, additional_terms=[tt, btt])
det_proc.range(55, 65)

# Next, we write a simple "wrapper" for some actual exogenous data that
# simplifies constructing out-of-sample exogenous arrays for forecasting.


class ExogenousProcess(DeterministicTerm):
    def __init__(self, data):
        self._data = data

    def __str__(self):
        return "Custom Exog Process"

    def _eq_attr(self):
        return (id(self._data), )

    def in_sample(self, index: pd.Index):
        return self._data.loc[index]

    def out_of_sample(self,
                      steps: int,
                      index: pd.Index,
                      forecast_index: pd.Index = None):
        forecast_index = self._extend_index(index, steps, forecast_index)
        return self._data.loc[forecast_index]


import numpy as np

gen = np.random.default_rng(98765432101234567890)
exog = pd.DataFrame(gen.integers(100, size=(300, 2)),
                    columns=["exog1", "exog2"])
exog.head()

ep = ExogenousProcess(exog)
tt = TimeTrend(constant=True, order=1)
# The in-sample index
idx = exog.index[:200]
det_proc = DeterministicProcess(idx, additional_terms=[tt, ep])

det_proc.in_sample().head()

det_proc.out_of_sample(10)

# ## Model Support
#
# The only model that directly supports `DeterministicProcess` is
# `AutoReg`. A custom term can be set using the `deterministic` keyword
# argument.
#
# **Note**: Using a custom term requires that `trend="n"` and
# `seasonal=False` so that all deterministic components must come from the
# custom deterministic term.

# ### Simulate Some Data
#
# Here we simulate some data that has an weekly seasonality captured by a
# Fourier series.

gen = np.random.default_rng(98765432101234567890)
idx = pd.RangeIndex(200)
det_proc = DeterministicProcess(idx, constant=True, period=52, fourier=2)
det_terms = det_proc.in_sample().to_numpy()
params = np.array([1.0, 3, -1, 4, -2])
exog = det_terms @ params
y = np.empty(200)
y[0] = det_terms[0] @ params + gen.standard_normal()
for i in range(1, 200):
    y[i] = 0.9 * y[i - 1] + det_terms[i] @ params + gen.standard_normal()
y = pd.Series(y, index=idx)
ax = y.plot()

# The model is then fit using the `deterministic` keyword argument.
# `seasonal` defaults to False but `trend` defaults to `"c"` so this needs
# to be changed.

from statsmodels.tsa.api import AutoReg

mod = AutoReg(y, 1, trend="n", deterministic=det_proc)
res = mod.fit()
print(res.summary())

# We can use the `plot_predict` to show the predicted values and their
# prediction interval. The out-of-sample deterministic values are
# automatically produced by the deterministic process passed to `AutoReg`.

fig = res.plot_predict(200, 200 + 2 * 52, True)

auto_reg_forecast = res.predict(200, 211)
auto_reg_forecast

# ## Using with other models
#
# Other models do not support `DeterministicProcess` directly.  We can
# instead manually pass any deterministic terms as `exog` to model that
# support exogenous values.
#
# Note that `SARIMAX` with exogenous variables is OLS with SARIMA errors
# so that the model is
#
# $$
# \begin{align*}
# \nu_t & = y_t - x_t \beta  \\
# (1-\phi(L))\nu_t & = (1+\theta(L))\epsilon_t.
# \end{align*}
# $$
#
# The parameters on deterministic terms are not directly comparable to
# `AutoReg` which evolves according to the equation
#
# $$
# (1-\phi(L)) y_t = x_t \beta + \epsilon_t.
# $$
#
# When $x_t$ contains only deterministic terms, these two representation
# are equivalent (assuming $\theta(L)=0$ so that there is no MA).
#

from statsmodels.tsa.api import SARIMAX

det_proc = DeterministicProcess(idx, period=52, fourier=2)
det_terms = det_proc.in_sample()

mod = SARIMAX(y, order=(1, 0, 0), trend="c", exog=det_terms)
res = mod.fit(disp=False)
print(res.summary())

# The forecasts are similar but differ since the parameters of the
# `SARIMAX` are estimated using MLE while `AutoReg` uses OLS.

sarimax_forecast = res.forecast(12, exog=det_proc.out_of_sample(12))
df = pd.concat([auto_reg_forecast, sarimax_forecast], axis=1)
df.columns = columns = ["AutoReg", "SARIMAX"]
df

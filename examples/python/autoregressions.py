#!/usr/bin/env python

# DO NOT EDIT
# Autogenerated from the notebook autoregressions.ipynb.
# Edit the notebook and then sync the output with this file.
#
# flake8: noqa
# DO NOT EDIT

# # Autoregressions
#
# This notebook introduces autoregression modeling using the `AutoReg`
# model. It also covers aspects of `ar_select_order` assists in selecting
# models that minimize an information criteria such as the AIC.
# An autoregressive model has dynamics given by
#
# $$ y_t = \delta + \phi_1 y_{t-1} + \ldots + \phi_p y_{t-p} + \epsilon_t.
# $$
#
# `AutoReg` also permits models with:
#
# * Deterministic terms (`trend`)
#   * `n`: No deterministic term
#   * `c`: Constant (default)
#   * `ct`: Constant and time trend
#   * `t`: Time trend only
# * Seasonal dummies (`seasonal`)
#   * `True` includes $s-1$ dummies where $s$ is the period of the time
# series (e.g., 12 for monthly)
# * Custom deterministic terms (`deterministic`)
#   * Accepts a `DeterministicProcess`
# * Exogenous variables (`exog`)
#   * A `DataFrame` or `array` of exogenous variables to include in the
# model
# * Omission of selected lags (`lags`)
#   * If `lags` is an iterable of integers, then only these are included
# in the model.
#
# The complete specification is
#
# $$ y_t = \delta_0 + \delta_1 t + \phi_1 y_{t-1} + \ldots + \phi_p
# y_{t-p} + \sum_{i=1}^{s-1} \gamma_i d_i + \sum_{j=1}^{m} \kappa_j x_{t,j}
# + \epsilon_t. $$
#
# where:
#
# * $d_i$ is a seasonal dummy that is 1 if $mod(t, period) = i$. Period 0
# is excluded if the model contains a constant (`c` is in `trend`).
# * $t$ is a time trend ($1,2,\ldots$) that starts with 1 in the first
# observation.
# * $x_{t,j}$ are exogenous regressors.  **Note** these are time-aligned
# to the left-hand-side variable when defining a model.
# * $\epsilon_t$ is assumed to be a white noise process.

# This first cell imports standard packages and sets plots to appear
# inline.

import matplotlib.pyplot as plt
import pandas as pd
import pandas_datareader as pdr
import seaborn as sns
from statsmodels.tsa.api import acf, graphics, pacf
from statsmodels.tsa.ar_model import AutoReg, ar_select_order

# This cell sets the plotting style, registers pandas date converters for
# matplotlib, and sets the default figure size.

sns.set_style("darkgrid")
pd.plotting.register_matplotlib_converters()
# Default figure size
sns.mpl.rc("figure", figsize=(16, 6))
sns.mpl.rc("font", size=14)

# The first set of examples uses the month-over-month growth rate in U.S.
# Housing starts that has not been seasonally adjusted. The seasonality is
# evident by the regular pattern of peaks and troughs. We set the frequency
# for the time series to "MS" (month-start) to avoid warnings when using
# `AutoReg`.

data = pdr.get_data_fred("HOUSTNSA", "1959-01-01", "2019-06-01")
housing = data.HOUSTNSA.pct_change().dropna()
# Scale by 100 to get percentages
housing = 100 * housing.asfreq("MS")
fig, ax = plt.subplots()
ax = housing.plot(ax=ax)

# We can start with an AR(3).  While this is not a good model for this
# data, it demonstrates the basic use of the API.

mod = AutoReg(housing, 3, old_names=False)
res = mod.fit()
print(res.summary())

# `AutoReg` supports the same covariance estimators as `OLS`.  Below, we
# use `cov_type="HC0"`, which is White's covariance estimator. While the
# parameter estimates are the same, all of the quantities that depend on the
# standard error change.

res = mod.fit(cov_type="HC0")
print(res.summary())

sel = ar_select_order(housing, 13, old_names=False)
sel.ar_lags
res = sel.model.fit()
print(res.summary())

# `plot_predict` visualizes forecasts.  Here we produce a large number of
# forecasts which show the string seasonality captured by the model.

fig = res.plot_predict(720, 840)

# `plot_diagnositcs` indicates that the model captures the key features in
# the data.

fig = plt.figure(figsize=(16, 9))
fig = res.plot_diagnostics(fig=fig, lags=30)

# ## Seasonal Dummies

# `AutoReg` supports seasonal dummies which are an alternative way to
# model seasonality.  Including the dummies shortens the dynamics to only an
# AR(2).

sel = ar_select_order(housing, 13, seasonal=True, old_names=False)
sel.ar_lags
res = sel.model.fit()
print(res.summary())

# The seasonal dummies are obvious in the forecasts which has a non-
# trivial seasonal component in all periods 10 years in to the future.

fig = res.plot_predict(720, 840)

fig = plt.figure(figsize=(16, 9))
fig = res.plot_diagnostics(lags=30, fig=fig)

# ## Seasonal Dynamics

# While `AutoReg` does not directly support Seasonal components since it
# uses OLS to estimate parameters, it is possible to capture seasonal
# dynamics using an over-parametrized Seasonal AR that does not impose the
# restrictions in the Seasonal AR.

yoy_housing = data.HOUSTNSA.pct_change(12).resample("MS").last().dropna()
_, ax = plt.subplots()
ax = yoy_housing.plot(ax=ax)

# We start by selecting a model using the simple method that only chooses
# the maximum lag.  All lower lags are automatically included. The maximum
# lag to check is set to 13 since this allows the model to next a Seasonal
# AR that has both a short-run AR(1) component and a Seasonal AR(1)
# component, so that
#
# $$ (1-\phi_s L^{12})(1-\phi_1 L)y_t = \epsilon_t $$
# which becomes
# $$ y_t = \phi_1 y_{t-1} +\phi_s Y_{t-12} - \phi_1\phi_s Y_{t-13} +
# \epsilon_t $$
#
# when expanded. `AutoReg` does not enforce the structure, but can
# estimate the nesting model
#
# $$ y_t = \phi_1 y_{t-1} +\phi_{12} Y_{t-12} - \phi_{13} Y_{t-13} +
# \epsilon_t. $$
#
# We see that all 13 lags are selected.

sel = ar_select_order(yoy_housing, 13, old_names=False)
sel.ar_lags

# It seems unlikely that all 13 lags are required.  We can set `glob=True`
# to search all $2^{13}$ models that include up to 13 lags.
#
# Here we see that the first three are selected, as is the 7th, and
# finally the 12th and 13th are selected.  This is superficially similar to
# the structure described above.
#
# After fitting the model, we take a look at the diagnostic plots that
# indicate that this specification appears to be adequate to capture the
# dynamics in the data.

sel = ar_select_order(yoy_housing, 13, glob=True, old_names=False)
sel.ar_lags
res = sel.model.fit()
print(res.summary())

fig = plt.figure(figsize=(16, 9))
fig = res.plot_diagnostics(fig=fig, lags=30)

# We can also include seasonal dummies.  These are all insignificant since
# the model is using year-over-year changes.

sel = ar_select_order(yoy_housing,
                      13,
                      glob=True,
                      seasonal=True,
                      old_names=False)
sel.ar_lags
res = sel.model.fit()
print(res.summary())

# ## Industrial Production
#
# We will use the industrial production index data to examine forecasting.

data = pdr.get_data_fred("INDPRO", "1959-01-01", "2019-06-01")
ind_prod = data.INDPRO.pct_change(12).dropna().asfreq("MS")
_, ax = plt.subplots(figsize=(16, 9))
ind_prod.plot(ax=ax)

# We will start by selecting a model using up to 12 lags.  An AR(13)
# minimizes the BIC criteria even though many coefficients are
# insignificant.

sel = ar_select_order(ind_prod, 13, "bic", old_names=False)
res = sel.model.fit()
print(res.summary())

# We can also use a global search which allows longer lags to enter if
# needed without requiring the shorter lags. Here we see many lags dropped.
# The model indicates there may be some seasonality in the data.

sel = ar_select_order(ind_prod, 13, "bic", glob=True, old_names=False)
sel.ar_lags
res_glob = sel.model.fit()
print(res.summary())

# `plot_predict` can be used to produce forecast plots along with
# confidence intervals. Here we produce forecasts starting at the last
# observation and continuing for 18 months.

ind_prod.shape

fig = res_glob.plot_predict(start=714, end=732)

# The forecasts from the full model and the restricted model are very
# similar. I also include an AR(5) which has very different dynamics

res_ar5 = AutoReg(ind_prod, 5, old_names=False).fit()
predictions = pd.DataFrame({
    "AR(5)":
    res_ar5.predict(start=714, end=726),
    "AR(13)":
    res.predict(start=714, end=726),
    "Restr. AR(13)":
    res_glob.predict(start=714, end=726),
})
_, ax = plt.subplots()
ax = predictions.plot(ax=ax)

# The diagnostics indicate the model captures most of the the dynamics in
# the data. The ACF shows a patters at the seasonal frequency and so a more
# complete seasonal model (`SARIMAX`) may be needed.

fig = plt.figure(figsize=(16, 9))
fig = res_glob.plot_diagnostics(fig=fig, lags=30)

# # Forecasting
#
# Forecasts are produced using the `predict` method from a results
# instance. The default produces static forecasts which are one-step
# forecasts. Producing multi-step forecasts requires using `dynamic=True`.
#
# In this next cell, we produce 12-step-heard forecasts for the final 24
# periods in the sample.  This requires a loop.
#
# **Note**: These are technically in-sample since the data we are
# forecasting was used to estimate parameters. Producing OOS forecasts
# requires two models.  The first must exclude the OOS period.  The second
# uses the `predict` method from the full-sample model with the parameters
# from the shorter sample model that excluded the OOS period.

import numpy as np

start = ind_prod.index[-24]
forecast_index = pd.date_range(start, freq=ind_prod.index.freq, periods=36)
cols = [
    "-".join(str(val) for val in (idx.year, idx.month))
    for idx in forecast_index
]
forecasts = pd.DataFrame(index=forecast_index, columns=cols)
for i in range(1, 24):
    fcast = res_glob.predict(start=forecast_index[i],
                             end=forecast_index[i + 12],
                             dynamic=True)
    forecasts.loc[fcast.index, cols[i]] = fcast
_, ax = plt.subplots(figsize=(16, 10))
ind_prod.iloc[-24:].plot(ax=ax, color="black", linestyle="--")
ax = forecasts.plot(ax=ax)

# ## Comparing to SARIMAX
#
# `SARIMAX` is an implementation of a Seasonal Autoregressive Integrated
# Moving Average with eXogenous regressors model.  It supports:
#
# * Specification of seasonal and nonseasonal AR and MA components
# * Inclusion of Exogenous variables
# * Full maximum-likelihood estimation using the Kalman Filter
#
# This model is more feature rich than `AutoReg`. Unlike `SARIMAX`,
# `AutoReg` estimates parameters using OLS.  This is faster and the problem
# is globally convex, and so there are no issues with local minima. The
# closed-form estimator and its performance are the key advantages of
# `AutoReg` over `SARIMAX` when comparing AR(P) models.  `AutoReg` also
# support seasonal dummies, which can be used with `SARIMAX` if the user
# includes them as exogenous regressors.

from statsmodels.tsa.api import SARIMAX

sarimax_mod = SARIMAX(ind_prod, order=((1, 5, 12, 13), 0, 0), trend="c")
sarimax_res = sarimax_mod.fit()
print(sarimax_res.summary())

sarimax_params = sarimax_res.params.iloc[:-1].copy()
sarimax_params.index = res_glob.params.index
params = pd.concat([res_glob.params, sarimax_params], axis=1, sort=False)
params.columns = ["AutoReg", "SARIMAX"]
params

# ## Custom Deterministic Processes
#
# The `deterministic` parameter allows a custom `DeterministicProcess` to
# be used. This allows for more complex deterministic terms to be
# constructed, for example one that includes seasonal components with two
# periods, or, as the next example shows, one that uses a Fourier series
# rather than seasonal dummies.

from statsmodels.tsa.deterministic import DeterministicProcess

dp = DeterministicProcess(housing.index, constant=True, period=12, fourier=2)
mod = AutoReg(housing, 2, trend="n", seasonal=False, deterministic=dp)
res = mod.fit()
print(res.summary())

fig = res.plot_predict(720, 840)

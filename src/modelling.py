"""Model fitting and validation, following the 6SSG3077 ML seminars.

- OLS baseline (ML1)
- Random forest tuned with GridSearchCV (ML2 + Validation seminar)
- Random KFold versus spatial GroupKFold cross-validation (extension: the
  seminars warn that nearby areas leak information between folds)
- Final evaluation on held-out spatial blocks, plus out-of-fold residuals
  for mapping and Moran's I
"""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.model_selection import (
    GridSearchCV, GroupKFold, GroupShuffleSplit, KFold, cross_val_predict,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_blocks(x, y, size: float) -> np.ndarray:
    """Label each point with the square block (size in metres) that contains it."""
    bx = np.floor(np.asarray(x) / size).astype(int).astype(str)
    by = np.floor(np.asarray(y) / size).astype(int).astype(str)
    return np.char.add(np.char.add(bx, "_"), by)


def scores(y_true, y_pred) -> dict:
    return {"RMSE": root_mean_squared_error(y_true, y_pred), "R2": r2_score(y_true, y_pred)}


def spatial_split(df: pd.DataFrame, groups, test_size: float, random_state: int):
    """Hold out whole blocks as the test set, so test cells are not neighbours of training cells."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(df, groups=groups))
    return df.iloc[train_idx].copy(), df.iloc[test_idx].copy()


def fit_ols(X_train, y_train):
    """Linear regression on standardised inputs, so coefficients are comparable (per 1 SD)."""
    model = make_pipeline(StandardScaler(), LinearRegression())
    model.fit(X_train, y_train)
    coefs = pd.Series(model[-1].coef_, index=X_train.columns, name="std_coef")
    return model, coefs


def tune_random_forest(X, y, groups, param_grid, n_splits, n_estimators, random_state):
    """Grid-search a random forest under random and spatial cross-validation.

    Returns the two fitted GridSearchCV objects and a summary table with the
    best settings, training RMSE and mean CV RMSE for each design.
    """
    designs = {
        "random KFold": KFold(n_splits=n_splits, shuffle=True, random_state=random_state),
        "spatial GroupKFold": GroupKFold(n_splits=n_splits),
    }
    searches, rows = {}, []
    for name, cv in designs.items():
        search = GridSearchCV(
            RandomForestRegressor(n_estimators=n_estimators, random_state=random_state, n_jobs=-1),
            param_grid, cv=cv, scoring="neg_root_mean_squared_error", n_jobs=1,
        )
        search.fit(X, y, groups=groups if isinstance(cv, GroupKFold) else None)
        searches[name] = search
        train_rmse = root_mean_squared_error(y, search.best_estimator_.predict(X))
        rows.append({
            "CV design": name,
            "best params": search.best_params_,
            "training RMSE": train_rmse,
            "mean CV RMSE": -search.best_score_,
        })
    return searches, pd.DataFrame(rows)


def run_crime_model(df, target, features, block_col, cfg):
    """Full pipeline for one crime group. `cfg` is the src.config module."""
    train, test = spatial_split(df, df[block_col], cfg.TEST_SIZE, cfg.RANDOM_STATE)
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]

    # 1. OLS baseline
    ols, ols_coefs = fit_ols(X_train, y_train)

    # 2. Random forest tuned under random vs spatial CV (training data only)
    searches, cv_table = tune_random_forest(
        X_train, y_train, train[block_col], cfg.RF_PARAM_GRID,
        cfg.N_SPLITS, cfg.N_ESTIMATORS, cfg.RANDOM_STATE,
    )

    # 3. One final evaluation on held-out blocks
    test_rows = [{"model": "OLS", **scores(y_test, ols.predict(X_test))}]
    for name, search in searches.items():
        test_rows.append({"model": f"Random forest (tuned with {name})",
                          **scores(y_test, search.best_estimator_.predict(X_test))})
    test_table = pd.DataFrame(test_rows)

    # 4. Out-of-fold predictions for every cell (spatially tuned settings),
    #    used to map residuals and test them for spatial autocorrelation
    final_rf = searches["spatial GroupKFold"].best_estimator_
    oof = cross_val_predict(
        clone(final_rf), df[features], df[target],
        cv=GroupKFold(n_splits=cfg.N_SPLITS), groups=df[block_col],
    )

    return {
        "train": train, "test": test,
        "ols": ols, "ols_coefs": ols_coefs,
        "searches": searches, "cv_table": cv_table,
        "test_table": test_table,
        "final_rf": final_rf,
        "oof_pred": pd.Series(oof, index=df.index),
        "oof_resid": df[target] - oof,
    }

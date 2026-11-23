import importlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.stats import ttest_ind

import analysis as a


@pytest.fixture
def data():
    rows = []
    for group, pair in enumerate(((1, 0), (0, 1), (1, 1))):
        for arm_index, arm in enumerate(a.ARMS):
            for i in range(12):
                spend = float((i % 4) * (arm_index + group + 1))
                rows.append(dict(recency=3, history_segment="1) $0 - $100", history=50.,
                                 mens=pair[0], womens=pair[1], zip_code="Urban", newbie=i % 2,
                                 channel=("Web", "Phone", "Multichannel")[i % 3],
                                 segment=arm, visit=int(i % 4 > 0),
                                 conversion=int(spend > 0), spend=spend))
    return pd.DataFrame(rows)


def test_import_has_no_output(capsys):
    importlib.reload(a)
    assert capsys.readouterr().out == ""


def test_validation_and_duplicate_preservation(data):
    assert a.validate_data(data) is data
    duplicate = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    assert len(a.validate_data(duplicate)) == len(data) + 1


@pytest.mark.parametrize("issue", ["empty", "field", "extra", "arm", "missing_arm", "binary",
                                  "negative", "text", "infinite", "missing", "conversion",
                                  "group", "category", "missing_newbie", "missing_channel", "missing_purchase"])
def test_invalid_data(data, issue):
    bad = data.copy()
    if issue == "empty":
        bad = bad.iloc[:0]
    elif issue == "field":
        bad = bad.drop(columns="history")
    elif issue == "extra":
        bad["extra"] = 1
    elif issue == "arm":
        bad.loc[0, "segment"] = "invalid"
    elif issue == "missing_arm":
        bad = bad[bad.segment != a.ARMS[0]]
    elif issue == "binary":
        bad.loc[0, "visit"] = 2
    elif issue == "negative":
        bad.loc[0, "spend"] = -1.
    elif issue == "text":
        bad["spend"] = bad["spend"].astype(str)
    elif issue == "infinite":
        bad.loc[0, "spend"] = np.inf
    elif issue == "missing":
        bad.loc[0, "spend"] = np.nan
    elif issue == "conversion":
        bad.loc[0, "conversion"] = 1
    elif issue == "group":
        bad.loc[0, ["mens", "womens"]] = 0
    elif issue == "missing_newbie":
        bad = bad[bad.newbie == 0]
    elif issue == "missing_channel":
        bad = bad[bad.channel != "Web"]
    elif issue == "missing_purchase":
        bad = bad[bad.mens != 0]
    else:
        bad.loc[0, "channel"] = ""
    with pytest.raises(ValueError):
        a.validate_data(bad)


def test_loading(data, tmp_path):
    path = tmp_path / "data.csv"
    data.to_csv(path, index=False)
    pd.testing.assert_frame_equal(a.load_data(path), data, check_like=True)


def test_business_metrics(data):
    table = a.business_metrics(data)
    row = table.loc[a.ARMS[0]]
    assert row["n"] == 36
    assert row["visit_rate"] == pytest.approx(.75)
    assert row["conversion_rate"] == pytest.approx(.75)
    assert row["rpc"] == pytest.approx(3.)
    assert row["buyer_spend"] == pytest.approx(4.)
    assert row["rpc"] == row["buyer_spend"] * row["conversion_rate"]


def test_welch_against_scipy():
    x, y = [0, 1, 4, 9], [0, 2, 1, 5, 3]
    result = a.welch_result(x, y)
    oracle = ttest_ind(x, y, equal_var=False)
    ci = oracle.confidence_interval()
    assert result["diff"] == pytest.approx(np.mean(x) - np.mean(y))
    assert result["p"] == pytest.approx(oracle.pvalue)
    assert a.welch_interval(x, y) == pytest.approx((ci.low, ci.high))


@pytest.mark.parametrize("x,y", [([], [1, 2]), ([1, 1], [1, 1]), ([np.nan, 2], [2, 3])])
def test_invalid_welch(x, y):
    with pytest.raises(ValueError):
        a.welch_result(x, y)


def test_proportions():
    result = a.proportion_result([1, 1, 0, 0], [1, 0, 0, 0])
    assert result["diff"] == .25
    assert result["low"] < result["diff"] < result["high"]
    assert result["p"] == pytest.approx(.4652088184521418)


def test_holm():
    assert a.holm([.01, .04, .03]) == pytest.approx([.03, .06, .06])
    with pytest.raises(ValueError):
        a.holm([np.nan])


def test_srm():
    table, statistic, p = a.srm_test(pd.DataFrame({"segment": [a.ARMS[0]] * 10 +
                                                            [a.ARMS[1]] * 20 + [a.ARMS[2]] * 30}))
    assert table.expected.to_list() == [20, 20, 20]
    assert statistic == pytest.approx(10)
    assert p == pytest.approx(np.exp(-5))


def test_labels(data):
    labels = a.purchase_groups(data)
    assert labels.iloc[[0, 36, 72]].tolist() == ["仅买过男装", "仅买过女装", "两类都买过"]


def test_selection_and_single_change(data):
    data["purchase_group"] = a.purchase_groups(data)
    strategy_a, strategy_b = a.select_policies(data)
    assert strategy_a == "No E-Mail"
    assert set(strategy_b) == {"No E-Mail"}
    equal = a.evaluate_policies(data, strategy_a, strategy_b)
    assert equal["diff"] == 0 and equal["p"] is None
    strategy_b.iloc[0] = a.ARMS[0]
    result = a.evaluate_policies(data, strategy_a, strategy_b)
    group = strategy_b.index[0]
    x = data.loc[(data.purchase_group == group) & (data.segment == a.ARMS[0]), "spend"]
    y = data.loc[(data.purchase_group == group) & (data.segment == strategy_a), "spend"]
    oracle = a.welch_result(x, y)
    assert result["diff"] == pytest.approx(oracle["diff"] / 3)
    assert result["p"] == pytest.approx(oracle["p"])
    assert result["low"] == pytest.approx(oracle["low"] / 3)


def test_multiple_changes(data):
    data["purchase_group"] = a.purchase_groups(data)
    strategy = pd.Series(a.ARMS[0], index=sorted(data.purchase_group.unique()))
    result = a.evaluate_policies(data, a.ARMS[2], strategy)
    # 三个等权群体全部换方案，手算加权方差和自由度。
    terms, denominator = [], 0.
    for group in strategy.index:
        for arm in (a.ARMS[0], a.ARMS[2]):
            values = data.loc[(data.purchase_group == group) & (data.segment == arm), "spend"]
            term = values.var(ddof=1) / len(values) / 9
            terms.append(term)
            denominator += term**2 / (len(values) - 1)
    variance = sum(terms)
    degrees = variance**2 / denominator
    expected = 2 * a.t.sf(abs(result["diff"]) / np.sqrt(variance), degrees)
    assert result["diff"] == pytest.approx(-3)
    assert result["p"] == pytest.approx(expected)
    assert result["high"] > result["low"]


def test_missing_cells(data):
    data["purchase_group"] = a.purchase_groups(data)
    bad = data.drop(data[(data.purchase_group == "仅买过男装") & (data.segment == a.ARMS[0])].index)
    with pytest.raises(ValueError, match="单元格"):
        a.select_policies(bad)
    with pytest.raises(ValueError):
        a.business_metrics(data.iloc[:0])


def test_seed_reproducibility(data):
    data["purchase_group"] = a.purchase_groups(data)
    pd.testing.assert_frame_equal(a.bootstrap_rpc(data, 30), a.bootstrap_rpc(data, 30))
    pd.testing.assert_frame_equal(a.bootstrap_interactions(data, 30), a.bootstrap_interactions(data, 30))
    # 平移一个群体的所有结果，不改变其两封邮件的相对效应。
    shifted = data.copy()
    shifted.loc[shifted.purchase_group == "仅买过男装", "spend"] += 100
    before = a.bootstrap_interactions(data, 30)
    after = a.bootstrap_interactions(shifted, 30)
    np.testing.assert_allclose(before.loc[:1, ["diff", "low", "high"]].to_numpy(dtype=float),
                               after.loc[:1, ["diff", "low", "high"]].to_numpy(dtype=float))


def test_comparison_families(data):
    table = a.comparisons(data)
    assert len(table) == 9
    np.testing.assert_allclose(table.holm_nine, a.holm(table.p))
    for _, family in table.groupby("metric"):
        np.testing.assert_allclose(family.holm_metric, a.holm(family.p))


def test_local_integration(tmp_path):
    root = Path(__file__).resolve().parents[1]
    candidates = [root / "data/hillstrom.csv", *root.glob("Kevin_Hillstrom*.csv")]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        pytest.skip("本地原始 CSV 不存在，未执行 64,000 行集成复现")
    output = tmp_path / "result.json"
    subprocess.run([sys.executable, str(root / "analysis.py"), str(path),
                    "--output-json", str(output)], check=True, capture_output=True)
    result = json.loads(output.read_text(encoding="utf8"))
    expected = dict(n=64000, p_all=.141812, p_emails=.041738, policy_difference=.010612,
                    policy_p=.957054, p_newbie=.051584, p_channel=.315287)
    for key, value in expected.items():
        assert result[key] == pytest.approx(value, abs=5e-7)
    assert list(result["counts"].values()) == [21307, 21387, 21306]
    assert result["rpc"][a.ARMS[0]] - result["rpc"][a.ARMS[2]] == pytest.approx(.769827, abs=5e-7)
    assert result["rpc"][a.ARMS[1]] - result["rpc"][a.ARMS[2]] == pytest.approx(.424412, abs=5e-7)
    np.testing.assert_allclose(a.holm([result["p_newbie"], result["p_channel"]]),
                               [.103168, .315287], atol=5e-7, rtol=0)
    assert result["srm"]["statistic"] == pytest.approx(.20253125)


def test_training_selects_different_actions(data):
    data["purchase_group"] = a.purchase_groups(data)
    group = "仅买过女装"
    train = data.copy()
    train.loc[(train.purchase_group == group) & (train.segment == a.ARMS[0]), "spend"] += 100
    strategy_a, strategy_b = a.select_policies(train)
    assert strategy_a == a.ARMS[0]
    assert strategy_b[group] == a.ARMS[0]
    assert strategy_b["两类都买过"] == a.ARMS[2]
    frozen = strategy_b.copy()
    a.evaluate_policies(data, strategy_a, strategy_b)
    pd.testing.assert_series_equal(strategy_b, frozen)


def test_profit_scenarios_existing_parameters(data):
    metrics, tests = a.business_metrics(data), a.comparisons(data)
    scenarios = a.profit_scenarios(metrics, tests)
    assert len(scenarios) == 12
    assert set(scenarios.margin) == {.2, .3, .4}
    assert set(scenarios.cost) == {.1, .2}
    # 合成数据 RPC 为男装 3、女装 4.5、不发 6，独立核对全部情景值。
    for row in scenarios.itertuples():
        uplift = {a.ARMS[0]: -3., a.ARMS[1]: -1.5}[row.arm]
        assert row.profit == pytest.approx((uplift * row.margin - row.cost) * 100000)
        assert row.per_customer == pytest.approx(row.profit / 100000)


def test_figure_inputs_and_png_output(data, tmp_path):
    from PIL import Image
    from plot_figures import generate_figures
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        table, scenarios, font = generate_figures(data, tmp_path)
    pd.testing.assert_frame_equal(table, a.comparisons(data))
    pd.testing.assert_frame_equal(scenarios, a.profit_scenarios(a.business_metrics(data), table))
    assert table.loc[table.metric == "spend", "diff"].to_list() == [-3., -1.5, -1.5]
    assert font
    for name, size in [("rpc_uplift_ci.png", (2200, 900)),
                       ("profit_sensitivity.png", (2000, 1000))]:
        path = tmp_path / name
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.size == size
            assert image.info["dpi"] == pytest.approx((200, 200), abs=.01)
            image.verify()

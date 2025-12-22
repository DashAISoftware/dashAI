import pyarrow as pa

from DashAI.back.types.categorical import Categorical


def test_categorical_init_string():
    categories = ["cat", "dog", "mouse"]
    test_array = pa.array(categories, from_pandas=True)

    cat = Categorical(values=test_array)

    assert cat.num_categories() == len(categories)

    s = cat.to_string()
    assert s["type"] == "Categorical"
    assert s["num_categories"] == len(categories)
    assert s["categories"] == [str(v) for v in categories]

    # Encodings

    for idx in range(len(categories)):
        key = cat.int2str(idx)
        assert cat.str2int(key) == idx

    # custom encoding
    custom_encoding = dict(enumerate(reversed(categories)))
    custom_cat = Categorical(values=test_array, encoding=custom_encoding)

    for exp_index, value in custom_encoding.items():
        assert custom_cat.str2int(value) == exp_index
        assert custom_cat.int2str(exp_index) == value


def test_categorical_init_int():
    categories = [1, 2, 3, 4, 5]
    test_array = pa.array(categories, from_pandas=True)

    cat = Categorical(values=test_array)

    assert cat.num_categories() == len(categories)

    s = cat.to_string()
    assert s["type"] == "Categorical"
    assert s["num_categories"] == len(categories)
    assert s["categories"] == [str(v) for v in categories]

    for i in range(len(categories)):
        label = cat.int2str(i)
        assert cat.str2int(label) == i

    custom_encoding = {value: i for i, value in enumerate(reversed(categories))}
    custom_cat = Categorical(values=test_array, encoding=custom_encoding)

    for value, exp_index in custom_encoding.items():
        assert custom_cat.str2int(value) == exp_index
        assert custom_cat.int2str(exp_index) == value

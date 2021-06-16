from hub.api.tensor import Tensor
from hub.core.storage.local import LocalProvider
from hub.core.storage.provider import StorageProvider
from hub.util.exceptions import TensorMetaMismatchError
import numpy as np
import pytest

from hub.api.dataset import Dataset
from hub.core.tests.common import parametrize_all_dataset_storages


def test_persist_local_flush(local_storage: LocalProvider):
    if local_storage is None:
        pytest.skip()

    ds = Dataset(local_storage.root, local_cache_size=512)
    ds.create_tensor("image")
    ds.image.extend(np.ones((4, 4096, 4096)))

    ds_new = Dataset(local_storage.root)
    assert len(ds_new) == 4

    assert ds_new.image.shape.lower == (4096, 4096)
    assert ds_new.image.shape.upper == (4096, 4096)

    np.testing.assert_array_equal(ds_new.image.numpy(), np.ones((4, 4096, 4096)))
    ds.delete()


def test_persist_with_local(local_storage):
    if local_storage is None:
        pytest.skip()

    with Dataset(local_storage.root, local_cache_size=512) as ds:

        ds.create_tensor("image")
        ds.image.extend(np.ones((4, 4096, 4096)))

        ds_new = Dataset(local_storage.root)
        assert len(ds_new) == 0  # shouldn't be flushed yet

    ds_new = Dataset(local_storage.root)
    assert len(ds_new) == 4

    assert ds_new.image.shape.lower == (4096, 4096)
    assert ds_new.image.shape.upper == (4096, 4096)

    np.testing.assert_array_equal(ds_new.image.numpy(), np.ones((4, 4096, 4096)))
    ds.delete()


def test_persist_local_clear_cache(local_storage: LocalProvider):
    if local_storage is None:
        pytest.skip()

    ds = Dataset(local_storage.root, local_cache_size=512)
    ds.create_tensor("image")
    ds.image.extend(np.ones((4, 4096, 4096)))
    ds.clear_cache()
    ds_new = Dataset(local_storage.root)
    assert len(ds_new) == 4

    assert ds_new.image.shape.lower == (4096, 4096)
    assert ds_new.image.shape.upper == (4096, 4096)

    np.testing.assert_array_equal(ds_new.image.numpy(), np.ones((4, 4096, 4096)))
    ds.delete()


@parametrize_all_dataset_storages
def test_populate_dataset(ds: Dataset):
    assert ds.meta.tensors == []
    ds.create_tensor("image")
    assert len(ds) == 0
    assert len(ds.image) == 0

    ds.image.extend(np.ones((4, 28, 28)))
    assert len(ds) == 4
    assert len(ds.image) == 4

    for _ in range(10):
        ds.image.append(np.ones((28, 28)))
    assert len(ds.image) == 14

    ds.image.extend([np.ones((28, 28)), np.ones((28, 28))])
    assert len(ds.image) == 16

    assert ds.meta.tensors == ["image"]


def test_stringify(memory_ds: Dataset):
    ds = memory_ds
    ds.create_tensor("image")
    ds.image.extend(np.ones((4, 4)))
    assert str(ds) == "Dataset(mode='a', tensors=['image'])"
    assert (
        str(ds[1:2])
        == "Dataset(mode='a', index=Index([slice(1, 2, 1)]), tensors=['image'])"
    )
    assert str(ds.image) == "Tensor(key='image')"
    assert str(ds[1:2].image) == "Tensor(key='image', index=Index([slice(1, 2, 1)]))"


def test_stringify_with_path(local_ds: Dataset):
    ds = local_ds
    assert local_ds.path
    assert str(ds) == f"Dataset(path={local_ds.path}, mode='a', tensors=[])"


@parametrize_all_dataset_storages
def test_compute_fixed_tensor(ds: Dataset):
    ds.create_tensor("image")
    ds.image.extend(np.ones((32, 28, 28)))
    np.testing.assert_array_equal(ds.image.numpy(), np.ones((32, 28, 28)))


@parametrize_all_dataset_storages
def test_compute_dynamic_tensor(ds: Dataset):
    ds.create_tensor("image")

    a1 = np.ones((32, 28, 28))
    a2 = np.ones((10, 36, 11))
    a3 = np.ones((29, 10))

    image = ds.image

    image.extend(a1)
    image.extend(a2)
    image.append(a3)

    expected_list = [*a1, *a2, a3]
    actual_list = image.numpy(aslist=True)

    for expected, actual in zip(expected_list, actual_list):
        np.testing.assert_array_equal(expected, actual)

    assert image.shape.lower == (28, 10)
    assert image.shape.upper == (36, 28)
    assert image.shape.is_dynamic


@parametrize_all_dataset_storages
def test_empty_samples(ds: Dataset):
    tensor = ds.create_tensor("with_empty", dtype="int64")

    a1 = np.arange(25 * 4 * 2).reshape(25, 4, 2)
    a2 = np.arange(5 * 10 * 50 * 2).reshape(5, 10, 50, 2)
    a3 = np.arange(0).reshape(0, 0, 2)
    a4 = np.arange(0).reshape(9, 0, 10, 2)

    tensor.append(a1)
    tensor.extend(a2)
    tensor.append(a3)
    tensor.extend(a4)

    actual_list = tensor.numpy(aslist=True)
    expected_list = [a1, *a2, a3, *a4]

    assert tensor.shape.lower == (0, 0, 2)
    assert tensor.shape.upper == (25, 50, 2)

    assert len(tensor) == 16
    for actual, expected in zip(actual_list, expected_list):
        np.testing.assert_array_equal(actual, expected)

    # test indexing individual empty samples with numpy while looping, this may seem redundant but this was failing before
    for actual_sample, expected in zip(ds, expected_list):
        actual = actual_sample.with_empty.numpy()
        np.testing.assert_array_equal(actual, expected)


@parametrize_all_dataset_storages
def test_scalar_samples(ds: Dataset):
    tensor = ds.create_tensor("scalars", dtype="int64")

    tensor.append(5)
    tensor.append(10)
    tensor.append(-99)
    tensor.extend([10, 1, 4])
    tensor.extend([1])

    assert len(tensor) == 7

    expected = np.array([5, 10, -99, 10, 1, 4, 1])
    np.testing.assert_array_equal(tensor.numpy(), expected)


@parametrize_all_dataset_storages
def test_iterate_dataset(ds):
    labels = [1, 9, 7, 4]
    ds.create_tensor("image")
    ds.create_tensor("label", dtype="int64")

    ds.image.extend(np.ones((4, 28, 28)))
    ds.label.extend(np.asarray(labels).reshape((4, 1)))

    for idx, sub_ds in enumerate(ds):
        img = sub_ds.image.numpy()
        label = sub_ds.label.numpy()
        np.testing.assert_array_equal(img, np.ones((28, 28)))
        assert label.shape == (1,)
        assert label == labels[idx]


def _check_tensor(tensor: Tensor, data: np.ndarray):
    np.testing.assert_array_equal(tensor.numpy(), data)


def test_compute_slices(memory_ds: Dataset):
    ds = memory_ds
    shape = (64, 16, 16, 16)
    data = np.arange(np.prod(shape)).reshape(shape)
    ds.create_tensor("data", dtype="int64")
    ds.data.extend(data)

    _check_tensor(ds.data[:], data[:])
    _check_tensor(ds.data[10:20], data[10:20])
    _check_tensor(ds.data[5], data[5])
    _check_tensor(ds.data[0][:], data[0][:])
    _check_tensor(ds.data[3, 3], data[3, 3])
    _check_tensor(ds.data[30:40, :, 8:11, 4], data[30:40, :, 8:11, 4])
    _check_tensor(ds.data[16, 4, 5, 1:3], data[16, 4, 5, 1:3])
    _check_tensor(ds[[0, 1, 2, 5, 6, 10, 60]].data, data[[0, 1, 2, 5, 6, 10, 60]])
    _check_tensor(ds.data[[0, 1, 2, 5, 6, 10, 60]], data[[0, 1, 2, 5, 6, 10, 60]])
    _check_tensor(ds.data[0][[0, 1, 2, 5, 6, 10, 15]], data[0][[0, 1, 2, 5, 6, 10, 15]])
    _check_tensor(ds[(0, 1, 6, 10, 15), :].data, data[(0, 1, 6, 10, 15), :])
    _check_tensor(ds.data[(0, 1, 6, 10, 15), :], data[(0, 1, 6, 10, 15), :])
    _check_tensor(ds.data[0][(0, 1, 6, 10, 15), :], data[0][(0, 1, 6, 10, 15), :])
    _check_tensor(ds.data[0, (0, 1, 5)], data[0, (0, 1, 5)])
    _check_tensor(ds.data[:, :][0], data[:, :][0])
    _check_tensor(ds.data[:, :][0:2], data[:, :][0:2])
    _check_tensor(ds.data[0, :][0:2], data[0, :][0:2])
    _check_tensor(ds.data[:, 0][0:2], data[:, 0][0:2])
    _check_tensor(ds.data[:, 0][0:2], data[:, 0][0:2])
    _check_tensor(ds.data[:, :][0][(0, 1, 2), 0], data[:, :][0][(0, 1, 2), 0])
    _check_tensor(ds.data[0][(0, 1, 2), 0][1], data[0][(0, 1, 2), 0][1])
    _check_tensor(ds.data[:, :][0][(0, 1, 2), 0][1], data[:, :][0][(0, 1, 2), 0][1])


def test_shape_property(memory_ds: Dataset):
    fixed = memory_ds.create_tensor("fixed_tensor")
    dynamic = memory_ds.create_tensor("dynamic_tensor")

    # dynamic shape property
    dynamic.extend(np.ones((32, 28, 28)))
    dynamic.extend(np.ones((16, 33, 9)))
    assert dynamic.shape.lower == (28, 9)
    assert dynamic.shape.upper == (33, 28)

    # fixed shape property
    fixed.extend(np.ones((9, 28, 28)))
    fixed.extend(np.ones((13, 28, 28)))
    assert fixed.shape.lower == (28, 28)
    assert fixed.shape.upper == (28, 28)


@pytest.mark.xfail(raises=TensorMetaMismatchError, strict=True)
def test_append_dtype_mismatch(memory_ds: Dataset):
    tensor = memory_ds.create_tensor("tensor", dtype="uint8")
    tensor.append(np.ones(100, dtype="float64"))

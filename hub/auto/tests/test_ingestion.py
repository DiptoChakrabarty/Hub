from hub.api.dataset import Dataset
from hub.auto.tests.common import get_dummy_data_path
from hub.auto.unstructured.image_classification import ImageClassification
import hub


def test_image_classification_simple():
    path = get_dummy_data_path("image_classification")
    destination = "./datasets/destination/classification"
    ds = Dataset(destination)
    unstructured = ImageClassification(source=path)
    unstructured.structure(ds, image_tensor_args={"sample_compression": "jpeg"})
    assert list(ds.tensors.keys()) == ["images", "labels"]
    assert ds.images.numpy().shape == (3, 200, 200, 3)
    assert ds.labels.numpy().shape == (3,)
    assert ds.labels.meta.class_names == ("class0", "class1", "class2")


def test_image_classification_sets():
    path = get_dummy_data_path("image_classification_with_sets")
    destination = "./datasets/destination/classification_sets"
    ds = Dataset(destination)
    unstructured = ImageClassification(source=path)
    unstructured.structure(ds, image_tensor_args={"sample_compression": "jpeg"})

    assert list(ds.tensors.keys()) == [
        "test/images",
        "test/labels",
        "train/images",
        "train/labels",
    ]
    assert ds["test/images"].numpy().shape == (3, 200, 200, 3)
    assert ds["test/labels"].numpy().shape == (3,)
    assert ds["test/labels"].meta.class_names == ("class0", "class1", "class2")

    assert ds["train/images"].numpy().shape == (3, 200, 200, 3)
    assert ds["train/labels"].numpy().shape == (3,)
    assert ds["train/labels"].meta.class_names == ("class0", "class1", "class2")

from hub.htypes import DEFAULT_HTYPE
from hub.core.meta.tensor_meta import TensorMeta
from hub.util.shape import Shape
from typing import List, Sequence, Union, Optional, Tuple

import numpy as np

from hub.core.tensor import (
    append_tensor,
    extend_tensor,
    read_samples_from_tensor,
    tensor_exists,
    update_samples_in_tensor,
)
from hub.core.typing import StorageProvider
from hub.util.exceptions import TensorDoesNotExistError
from hub.core.index import Index


class Tensor:
    def __init__(
        self,
        key: str,
        storage: StorageProvider,
        index: Optional[Index] = None,
    ):
        """Initializes a new tensor.

        Note:
            This operation does not create a new tensor in the storage provider,
            and should normally only be performed by Hub internals.

        Args:
            key (str): The internal identifier for this tensor.
            storage (StorageProvider): The storage provider for the parent dataset.
            index: The Index object restricting the view of this tensor.
                Can be an int, slice, or (used internally) an Index object.

        Raises:
            TensorDoesNotExistError: If no tensor with `key` exists and a `tensor_meta` was not provided.
        """
        self.key = key
        self.storage = storage
        self.index = index or Index()

        if not tensor_exists(self.key, self.storage):
            raise TensorDoesNotExistError(self.key)

    def extend(self, array: Union[np.ndarray, Sequence[np.ndarray]]):
        """Extends a tensor by appending multiple elements from a sequence.
        Accepts a sequence of numpy arrays or a single batched numpy array.

        Example:
            >>> len(image)
            0
            >>> image.extend(np.zeros((100, 28, 28, 1)))
            >>> len(image)
            100

        Args:
            array: The data to add to the tensor.
                The length should be equal to the number of samples to add.
        """
        if isinstance(array, np.ndarray):
            extend_tensor(array, self.key, storage=self.storage)
        else:
            for sample in array:
                self.append(sample)

    def append(self, array: np.ndarray):
        """Appends a sample to the end of a tensor.

        Example:
            >>> len(image)
            0
            >>> image.append(np.zeros((28, 28, 1)))
            >>> len(image)
            1

        Args:
            array (np.ndarray): The data to add to the tensor.
        """

        append_tensor(array, self.key, storage=self.storage)

    @property
    def meta(self):
        return TensorMeta.load(self.key, self.storage)

    @property
    def shape(self):
        return Shape(self.meta.min_shape, self.meta.max_shape)

    def __len__(self):
        """Returns the length of the primary axis of a tensor."""
        return self.meta.length

    def __getitem__(
        self,
        item: Union[int, slice, List[int], Tuple[Union[int, slice, Tuple[int]]], Index],
    ):
        return Tensor(self.key, self.storage, index=self.index[item])

    def __setitem__(
        self,
        item: Union[int, slice, List[int], Tuple[Union[int, slice, Tuple[int]]], Index],
        value: Union[np.ndarray, Sequence[np.ndarray]],
    ):
        if isinstance(value, np.ndarray):
            update_samples_in_tensor(value, self.key, self.storage, self.index[item])
        else:
            raise NotImplementedError(
                "Tensor update for Sequence[np.ndarray] not currently supported!"
            )

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def numpy(self, aslist=False) -> Union[np.ndarray, List[np.ndarray]]:
        """Computes the contents of a tensor in numpy format.

        Args:
            aslist (bool): If True, a list of np.ndarrays will be returned. Helpful for dynamic tensors.
                If False, a single np.ndarray will be returned unless the samples are dynamically shaped, in which case
                an error is raised.

        Raises:
            DynamicTensorNumpyError: If reading a dynamically-shaped array slice without `aslist=True`.

        Returns:
            A numpy array containing the data represented by this tensor.
        """

        return read_samples_from_tensor(
            self.key, self.storage, index=self.index, aslist=aslist
        )

    def __str__(self):
        index_str = f", index={self.index}"
        if self.index.is_trivial():
            index_str = ""
        return f"Tensor(key={repr(self.key)}{index_str})"

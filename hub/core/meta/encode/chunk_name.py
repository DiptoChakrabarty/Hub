from io import BytesIO
from typing import Tuple
import numpy as np
from uuid import uuid4


CHUNK_ID_BITS = 64
CHUNK_NAME_ENCODING_DTYPE = np.uint64


# entry structure:
# [chunk_id, num_chunks, num_samples_per_chunk, last_index]

# index definitions:
CHUNK_ID_INDEX = 0
LAST_INDEX_INDEX = 1


def _generate_chunk_id() -> CHUNK_NAME_ENCODING_DTYPE:
    return CHUNK_NAME_ENCODING_DTYPE(uuid4().int >> CHUNK_ID_BITS)


def _chunk_name_from_id(id: CHUNK_NAME_ENCODING_DTYPE) -> str:
    return hex(id)[2:]


def _chunk_id_from_name(name: str) -> CHUNK_NAME_ENCODING_DTYPE:
    return int("0x" + name, 16)


class ChunkNameEncoder:
    def __init__(self):
        self._encoded = None
        self._connectivity = None

    def tobytes(self) -> memoryview:
        bio = BytesIO()
        np.savez(bio, names=self._encoded, connectivity=self._connectivity)
        return bio.getbuffer()

    @property
    def num_chunks(self) -> int:
        if self._encoded is None:
            return 0
        return len(self._encoded)

    @property
    def num_samples(self) -> int:
        if self._encoded is None:
            return 0
        return int(self._encoded[-1, LAST_INDEX_INDEX] + 1)

    def get_name_for_chunk(self, idx) -> str:
        return _chunk_name_from_id(self._encoded[:, CHUNK_ID_INDEX][idx])

    def get_local_sample_index(self, global_sample_index: int, chunk_index: int):
        # TODO: explain what's going on here

        if global_sample_index < 0:
            raise Exception()  # TODO

        if chunk_index == 0:
            return global_sample_index

        last_entry = self._encoded[chunk_index - 1]
        last_index = last_entry[LAST_INDEX_INDEX]

        return int(global_sample_index - last_index)

    def get_chunk_names(
        self, sample_index: int, return_indices: bool = False
    ) -> Tuple[str]:
        """Returns the chunk names that correspond to `sample_index`."""

        if self.num_samples == 0:
            raise IndexError(
                f"Index {sample_index} is out of bounds for an empty chunk names encoding."
            )

        if sample_index < 0:
            sample_index = (self.num_samples) + sample_index

        idx = np.searchsorted(self._encoded[:, LAST_INDEX_INDEX], sample_index)
        names = [_chunk_name_from_id(self._encoded[idx, CHUNK_ID_INDEX])]
        indices = [idx]

        # if accessing last index, check connectivity!
        while (
            self._encoded[idx, LAST_INDEX_INDEX] == sample_index
            and self._connectivity[idx]
        ):
            idx += 1
            name = _chunk_name_from_id(self._encoded[idx, CHUNK_ID_INDEX])
            names.append(name)
            indices.append(idx)

        if return_indices:
            return tuple(names), indices

        return tuple(names)

    def extend_chunk(self, num_samples: int, connected_to_next: bool = False) -> str:
        if num_samples <= 0:
            raise ValueError(
                f"When extending, `num_samples` should be > 0. Got {num_samples}."
            )

        if self.num_samples == 0:
            raise Exception(
                "Cannot extend the previous chunk because it doesn't exist."
            )

        if self._connectivity[-1] == 1:
            # TODO: custom exception
            raise Exception(
                "Cannot extend a chunk that is already marked as `connected_to_next`."
            )

        last_entry = self._encoded[-1]
        last_entry[LAST_INDEX_INDEX] += num_samples
        self._connectivity[-1] = connected_to_next

        return _chunk_name_from_id(last_entry[CHUNK_ID_INDEX])

    def append_chunk(self, num_samples: int, connected_to_next: bool = False) -> str:
        if num_samples < 0:
            raise ValueError(
                f"When appending, `num_samples` should be >= 0. Got {num_samples}."
            )

        if self.num_samples == 0:
            if num_samples == 0:
                raise Exception("First num samples cannot be 0.")  # TODO: exceptions.py

            id = _generate_chunk_id()
            self._encoded = np.array(
                [[id, num_samples - 1]], dtype=CHUNK_NAME_ENCODING_DTYPE
            )
            self._connectivity = np.array([connected_to_next], dtype=bool)
        else:
            if num_samples == 0 and self._connectivity[-1] == 0:
                raise Exception(
                    "num_samples cannot be 0 unless the previous chunk was connected to next."
                )  # TODO: exceptions.py

            id = _generate_chunk_id()

            # TODO: check if we can use the previous chunk name (and add the delimited range)
            last_index = self.num_samples - 1

            new_entry = np.array(
                [[id, last_index + num_samples]],
                dtype=CHUNK_NAME_ENCODING_DTYPE,
            )
            self._encoded = np.concatenate([self._encoded, new_entry])
            self._connectivity = np.concatenate(
                [self._connectivity, [connected_to_next]]
            )

        last_entry = self._encoded[-1]
        return _chunk_name_from_id(last_entry[CHUNK_ID_INDEX])


def _validate_num_samples(num_samples: int):
    if num_samples <= 0:
        raise ValueError(f"`num_count` should be > 0. Got {num_samples}.")

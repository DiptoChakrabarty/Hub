from typing import Union, Iterable
from multiprocessing.pool import ThreadPool
from hub.util.exceptions import FileAtPathException, DirectoryAtPathException
from hub.core.storage.provider import StorageProvider
import os


class LocalProvider(StorageProvider):
    """Provider class for using the local filesystem."""

    def __init__(self, root: str):
        """Initializes the LocalProvider.

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")

        Args:
            root (str): The root of the provider. All read/write request keys will be appended to root."

        Raises:
            FileAtPathException: If the root is a file instead of a directory.
        """
        if os.path.isfile(root):
            raise FileAtPathException(root)
        self.root = root

    def __getitem__(self, paths: Union[str, Iterable[str]]):
        """Gets the object present at the path within the given byte range.

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")
            my_data = local_provider["abc.txt"]

        Args:
            path (str): The path relative to the root of the provider.

        Returns:
            bytes: The bytes of the object present at the path.

        Raises:
            KeyError: If an object is not found at the path.
            DirectoryAtPathException: If a directory is found at the path.
            Exception: Any other exception encountered while trying to fetch the object.
        """

        def read_file(path):
            full_path = self._check_is_file(path)
            file = open(full_path, "rb")
            return file.read()

        try:
            if isinstance(paths, str):
                return read_file(paths)
            with ThreadPool() as pool:
                return pool.map(read_file, (paths,))

        except DirectoryAtPathException:
            raise
        except FileNotFoundError:
            raise KeyError
        except Exception:
            raise

    def __setitem__(
        self, paths: Union[str, Iterable[str]], values: Union[bytes, Iterable[bytes]]
    ):
        """Sets the object present at the path with the value

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")
            local_provider["abc.txt"] = b"abcd"

        Args:
            path (str): the path relative to the root of the provider.
            value (bytes): the value to be assigned at the path.

        Raises:
            Exception: If unable to set item due to directory at path or permission or space issues.
            FileAtPathException: If the directory to the path is a file instead of a directory.
        """

        def write(path_value):
            path, value = path_value
            full_path = self._check_is_file(path)
            directory = os.path.dirname(full_path)
            if os.path.isfile(directory):
                raise FileAtPathException(directory)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            file = open(full_path, "wb")
            file.write(value)

        try:
            if isinstance(paths, str):
                write((paths, values))
            else:
                with ThreadPool() as pool:
                    pool.map(write, list(zip(paths, values)))
        except Exception:
            raise

    def __delitem__(self, path: str):
        """Delete the object present at the path.

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")
            del local_provider["abc.txt"]

        Args:
            path (str): the path to the object relative to the root of the provider.

        Raises:
            KeyError: If an object is not found at the path.
            DirectoryAtPathException: If a directory is found at the path.
            Exception: Any other exception encountered while trying to fetch the object.
        """
        try:
            full_path = self._check_is_file(path)
            os.remove(full_path)
        except DirectoryAtPathException:
            raise
        except FileNotFoundError:
            raise KeyError
        except Exception:
            raise

    def __iter__(self):
        """Generator function that iterates over the keys of the provider.

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")
            for my_data in local_provider:
                pass

        Yields:
            str: the path of the object that it is iterating over, relative to the root of the provider.
        """
        yield from self._list_keys()

    def __len__(self):
        """Returns the number of files present inside the root of the provider.

        Example:
            local_provider = LocalProvider("/home/ubuntu/Documents/")
            len(local_provider)

        Returns:
            int: the number of files present inside the root.
        """
        return len(self._list_keys())

    def _list_keys(self):
        """Helper function that lists all the objects present at the root of the Provider.

        Returns:
            list: list of all the objects found at the root of the Provider.
        """
        ls = []
        for root, dirs, files in os.walk(self.root):
            for file in files:
                ls.append(os.path.relpath(os.path.join(root, file), self.root))
        return ls

    def _check_is_file(self, path: str):
        """Checks if the path is a file. Returns the full_path to file if True.

        Args:
            path (str): the path to the object relative to the root of the provider.

        Returns:
            str: the full path to the requested file.

        Raises:
            DirectoryAtPathException: If a directory is found at the path.
        """
        full_path = os.path.join(self.root, path)
        if os.path.isdir(full_path):
            raise DirectoryAtPathException
        return full_path


if __name__ == "__main__":
    local_provider = LocalProvider(
        "./test/hub2/core/storage/test/test_storage_provider_1"
    )
    local_provider[("fbdfbdfb", "dfbdfb")] = (b"dfbrberb", b"fbdfb")
    print(local_provider["fbdfbdfb"])

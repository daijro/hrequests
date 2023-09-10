import os
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from io import BufferedReader
from typing import Any, Dict, Iterator, List, Mapping, MutableMapping, Optional, Tuple, Union

from urllib3.fields import RequestField
from urllib3.filepost import encode_multipart_formdata


class FileUtils:
    basestring = (str, bytes)

    @staticmethod
    def to_items_list(value: Union[dict, tuple, list]) -> List[Tuple[str, Any]]:
        if isinstance(value, Mapping):
            value = value.items()
        return list(value)

    @staticmethod
    def _guess_filename(obj) -> Optional[str]:
        '''Tries to guess the filename of the given object.'''
        name = getattr(obj, 'name', None)
        if name and isinstance(name, FileUtils.basestring) and name[0] != "<" and name[-1] != ">":
            return os.path.basename(name)  # type: ignore

    @staticmethod
    def get_fields(data: Union[dict, tuple]) -> Iterator[Tuple[str, bytes]]:
        fields = FileUtils.to_items_list(data)
        for field, val in fields:
            if isinstance(val, FileUtils.basestring) or not hasattr(val, "__iter__"):
                val = (val,)
            for v in val:
                if v is None:
                    continue
                if not isinstance(v, bytes):
                    v = str(v)
                yield (
                    field.decode("utf-8") if isinstance(field, bytes) else field,
                    v.encode("utf-8") if isinstance(v, str) else v,
                )

    @staticmethod
    def encode_files(
        files: Dict[str, Union[BufferedReader, tuple]], data: Optional[Union[dict, tuple]] = None
    ) -> Tuple[bytes, str]:
        """
        Build the body for a multipart/form-data request.
        Will encode files when passed as a dict or a list of tuples.

        (file_name, file_obj[, content_type[, custom_headers]])
        """
        fields = list(FileUtils.get_fields(data)) if data else []

        for k, v in FileUtils.to_items_list(files):
            # support for explicit filename
            if isinstance(v, (tuple, list)):
                assert len(v) in range(
                    2, 5
                ), "Tuple/list must be (file_name, file_obj[, content_type[, custom_headers]])"
                file = File(*v)
            else:
                file = File(FileUtils._guess_filename(v) or k, v)

            rf: RequestField = RequestField(
                name=k, data=file.fdata, filename=file.file_name, headers=file.custom_headers
            )
            rf.make_multipart(content_type=file.content_type)
            fields.append(rf)

        return encode_multipart_formdata(fields)


@dataclass
class File:
    file_name: str
    file_obj: Union[BufferedReader, str, bytes, bytearray]
    content_type: Optional[str] = None
    custom_headers: Optional[dict] = None

    def __post_init__(self) -> None:
        # get the file data
        if isinstance(self.file_obj, BufferedReader):
            self.fdata = self.file_obj.read()
        else:
            self.fdata = self.file_obj


class CaseInsensitiveDict(MutableMapping):
    '''
    Origin: requests library (https://github.com/psf/requests)
    A case-insensitive ``dict``-like object.
    '''

    def __init__(self, data=None, **kwargs):
        self._store = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        '''Like iteritems(), but with all lowercase keys.'''
        return ((lowerkey, keyval[1]) for (lowerkey, keyval) in self._store.items())

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))

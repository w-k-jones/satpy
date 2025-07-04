#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2022 Satpy developers
#
# This file is part of satpy.
#
# satpy is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# satpy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# satpy.  If not, see <http://www.gnu.org/licenses/>.
"""Scene object to hold satellite data."""
from __future__ import annotations

import logging
import os
import warnings
from collections.abc import Iterable
from typing import Any, Callable

import numpy as np
import xarray as xr
from pyresample.geometry import AreaDefinition, BaseDefinition, CoordinateDefinition, SwathDefinition
from xarray import DataArray

from satpy.area import get_area_def
from satpy.composites import IncompatibleAreas
from satpy.composites.config_loader import load_compositor_configs_for_sensors
from satpy.dataset import DataID, DataQuery, DatasetDict, combine_metadata, dataset_walker, replace_anc
from satpy.dependency_tree import DependencyTree
from satpy.node import CompositorNode, MissingDependencies, ReaderNode
from satpy.readers.core.loading import load_readers
from satpy.utils import convert_remote_files_to_fsspec, get_storage_options_from_reader_kwargs

LOG = logging.getLogger(__name__)


def _get_area_resolution(area):
    """Attempt to retrieve resolution from AreaDefinition."""
    try:
        resolution = max(area.pixel_size_x, area.pixel_size_y)
    except AttributeError:
        resolution = max(area.lats.attrs["resolution"], area.lons.attrs["resolution"])
    return resolution


def _aggregate_data_array(data_array, func, **coarsen_kwargs):
    """Aggregate xr.DataArray."""
    res = data_array.coarsen(**coarsen_kwargs)
    if callable(func):
        out = res.reduce(func)
    else:
        out = getattr(res, func)()
    return out


class DelayedGeneration(KeyError):
    """Mark that a dataset can't be generated without further modification."""

    pass


class Scene:
    """The Almighty Scene Class.

    Example usage::

        from satpy import Scene
        from glob import glob

        # create readers and open files
        scn = Scene(filenames=glob('/path/to/files/*'), reader='viirs_sdr')

        # load datasets from input files
        scn.load(['I01', 'I02'])

        # resample from satellite native geolocation to builtin 'eurol' Area
        new_scn = scn.resample('eurol')

        # save all resampled datasets to geotiff files in the current directory
        new_scn.save_datasets()

    """

    def __init__(self, filenames=None, reader=None, filter_parameters=None,
                 reader_kwargs=None):
        """Initialize Scene with Reader and Compositor objects.

        To load data `filenames` and preferably `reader` must be specified::

            scn = Scene(filenames=glob('/path/to/viirs/sdr/files/*'), reader='viirs_sdr')


        If ``filenames`` is provided without ``reader`` then the available readers
        will be searched for a Reader that can support the provided files. This
        can take a considerable amount of time so it is recommended that
        ``reader`` always be provided. Note without ``filenames`` the Scene is
        created with no Readers available. When a Scene is created with no Readers,
        each xarray.DataArray must be added manually::

            scn = Scene()
            scn['my_dataset'] = DataArray(my_data_array, attrs={})

        The `attrs` dictionary contains the metadata for the data. See
        :ref:`dataset_metadata` for more information.

        Further, notice that it is also possible to load a combination of files
        or sets of files each requiring their specific reader. For that
        ``filenames`` needs to be a `dict` (see parameters list below), e.g.::

            scn = Scene(filenames={'nwcsaf-pps_nc': glob('/path/to/nwc/saf/pps/files/*'),
                                   'modis_l1b': glob('/path/to/modis/lvl1/files/*')})


        Args:
            filenames (Iterable or dict): A sequence of files that will be used to load data from. A ``dict`` object
                                          should map reader names to a list of filenames for that reader.
            reader (str or list): The name of the reader to use for loading the data or a list of names.
            filter_parameters (dict): Specify loaded file filtering parameters.
                                      Shortcut for `reader_kwargs['filter_parameters']`.
            reader_kwargs (dict): Keyword arguments to pass to specific reader instances.
                Either a single dictionary that will be passed onto to all
                reader instances, or a dictionary mapping reader names to
                sub-dictionaries to pass different arguments to different
                reader instances.

                Keyword arguments for remote file access are also given in this dictionary.
                See `documentation <https://satpy.readthedocs.io/en/stable/remote_reading.html>`_
                for usage examples.

        """
        self.attrs = dict()

        storage_options, cleaned_reader_kwargs = get_storage_options_from_reader_kwargs(reader_kwargs)

        if filter_parameters:
            if cleaned_reader_kwargs is None:
                cleaned_reader_kwargs = {}
            else:
                cleaned_reader_kwargs = cleaned_reader_kwargs.copy()
            cleaned_reader_kwargs.setdefault("filter_parameters", {}).update(filter_parameters)

        if filenames and isinstance(filenames, str):
            raise ValueError("'filenames' must be a list of files: Scene(filenames=[filename])")

        if filenames:
            filenames = convert_remote_files_to_fsspec(filenames, storage_options)

        self._readers = self._create_reader_instances(filenames=filenames,
                                                      reader=reader,
                                                      reader_kwargs=cleaned_reader_kwargs)
        self._datasets = DatasetDict()
        self._wishlist = set()
        self._dependency_tree = DependencyTree(self._readers)
        self._resamplers = {}

    @property
    def wishlist(self):
        """Return a copy of the wishlist."""
        return self._wishlist.copy()

    def _ipython_key_completions_(self):
        return [x["name"] for x in self._datasets.keys()]

    def _create_reader_instances(self,
                                 filenames=None,
                                 reader=None,
                                 reader_kwargs=None):
        """Find readers and return their instances."""
        return load_readers(filenames=filenames,
                            reader=reader,
                            reader_kwargs=reader_kwargs)

    @property
    def sensor_names(self) -> set[str]:
        """Return sensor names for the data currently contained in this Scene.

        Sensor information is collected from data contained in the Scene
        whether loaded from a reader or generated as a composite with
        :meth:`load` or added manually using ``scn["name"] = data_arr``).
        Sensor information is also collected from any loaded readers.
        In some rare cases this may mean that the reader includes sensor
        information for data that isn't actually loaded or even available.

        """
        contained_sensor_names = self._contained_sensor_names()
        reader_sensor_names = set([sensor for reader_instance in self._readers.values()
                                   for sensor in reader_instance.sensor_names])
        return contained_sensor_names | reader_sensor_names

    def _contained_sensor_names(self) -> set[str]:
        sensor_names = set()
        for data_arr in self.values():
            if "sensor" not in data_arr.attrs:
                continue
            if isinstance(data_arr.attrs["sensor"], str):
                sensor_names.add(data_arr.attrs["sensor"])
            elif isinstance(data_arr.attrs["sensor"], set):
                sensor_names.update(data_arr.attrs["sensor"])
        return sensor_names

    @property
    def start_time(self):
        """Return the start time of the contained data.

        If no data is currently contained in the Scene then loaded readers
        will be consulted.

        """
        start_times = [data_arr.attrs["start_time"] for data_arr in self.values()
                       if "start_time" in data_arr.attrs]
        if not start_times:
            start_times = self._reader_times("start_time")
        if not start_times:
            return None
        return min(start_times)

    @property
    def end_time(self):
        """Return the end time of the file.

        If no data is currently contained in the Scene then loaded readers
        will be consulted. If no readers are loaded then the
        :attr:`Scene.start_time` is returned.

        """
        end_times = [data_arr.attrs["end_time"] for data_arr in self.values()
                     if "end_time" in data_arr.attrs]
        if not end_times:
            end_times = self._reader_times("end_time")
        if not end_times:
            return self.start_time
        return max(end_times)

    def _reader_times(self, time_prop_name):
        return [getattr(reader, time_prop_name) for reader in self._readers.values()]

    @property
    def missing_datasets(self):
        """Set of DataIDs that have not been successfully loaded."""
        return set(self._wishlist) - set(self._datasets.keys())

    def _compare_areas(self, datasets=None, compare_func=max):
        """Compare areas for the provided datasets.

        Args:
            datasets (Iterable): Datasets whose areas will be compared. Can
                                 be either `xarray.DataArray` objects or
                                 identifiers to get the DataArrays from the
                                 current Scene. Defaults to all datasets.
                                 This can also be a series of area objects,
                                 typically AreaDefinitions.
            compare_func (Callable): `min` or `max` or other function used to
                                     compare the dataset's areas.

        """
        if datasets is None:
            datasets = list(self.values())

        areas = self._gather_all_areas(datasets)

        if isinstance(areas[0], AreaDefinition):
            first_crs = areas[0].crs
            if not all(ad.crs == first_crs for ad in areas[1:]):
                raise ValueError("Can't compare areas with different "
                                 "projections.")
            return self._compare_area_defs(compare_func, areas)
        return self._compare_swath_defs(compare_func, areas)

    @staticmethod
    def _compare_area_defs(compare_func: Callable, area_defs: list[AreaDefinition]) -> list[AreaDefinition]:
        def _key_func(area_def: AreaDefinition) -> tuple:
            """Get comparable version of area based on resolution.

            Pixel size x is the primary comparison parameter followed by
            the y dimension pixel size. The extent of the area and the
            name (area_id) of the area are also used to act as
            "tiebreakers" between areas of the same resolution.

            """
            pixel_size_x_inverse = 1. / abs(area_def.pixel_size_x)
            pixel_size_y_inverse = 1. / abs(area_def.pixel_size_y)
            area_id = area_def.area_id
            return pixel_size_x_inverse, pixel_size_y_inverse, area_def.area_extent, area_id
        return compare_func(area_defs, key=_key_func)

    @staticmethod
    def _compare_swath_defs(compare_func: Callable, swath_defs: list[SwathDefinition]) -> list[SwathDefinition]:
        def _key_func(swath_def: SwathDefinition) -> tuple:
            attrs = getattr(swath_def.lons, "attrs", {})
            lon_ds_name = attrs.get("name")
            rev_shape = swath_def.shape[::-1]
            return rev_shape + (lon_ds_name,)
        return compare_func(swath_defs, key=_key_func)

    def _gather_all_areas(self, datasets):
        """Gather all areas from datasets.

        They have to be of the same type, and at least one dataset should have
        an area.
        """
        areas = []
        for ds in datasets:
            if isinstance(ds, BaseDefinition):
                areas.append(ds)
                continue
            elif not isinstance(ds, DataArray):
                ds = self[ds]
            area = ds.attrs.get("area")
            areas.append(area)
        areas = [x for x in areas if x is not None]
        if not areas:
            raise ValueError("No dataset areas available")
        if not all(isinstance(x, type(areas[0]))
                   for x in areas[1:]):
            raise ValueError("Can't compare areas of different types")
        return areas

    def finest_area(self, datasets=None):
        """Get highest resolution area for the provided datasets.

        Args:
            datasets (Iterable): Datasets whose areas will be compared. Can
                                 be either `xarray.DataArray` objects or
                                 identifiers to get the DataArrays from the
                                 current Scene. Defaults to all datasets.

        """
        return self._compare_areas(datasets=datasets, compare_func=max)

    def max_area(self, datasets=None):
        """Get highest resolution area for the provided datasets. Deprecated.

        Deprecated.  Use :meth:`finest_area` instead.

        Args:
            datasets (Iterable): Datasets whose areas will be compared. Can
                                 be either `xarray.DataArray` objects or
                                 identifiers to get the DataArrays from the
                                 current Scene. Defaults to all datasets.

        """
        warnings.warn(
            "'max_area' is deprecated, use 'finest_area' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.finest_area(datasets=datasets)

    def coarsest_area(self, datasets=None):
        """Get lowest resolution area for the provided datasets.

        Args:
            datasets (Iterable): Datasets whose areas will be compared. Can
                                 be either `xarray.DataArray` objects or
                                 identifiers to get the DataArrays from the
                                 current Scene. Defaults to all datasets.

        """
        return self._compare_areas(datasets=datasets, compare_func=min)

    def min_area(self, datasets=None):
        """Get lowest resolution area for the provided datasets. Deprecated.

        Deprecated.  Use :meth:`coarsest_area` instead.

        Args:
            datasets (Iterable): Datasets whose areas will be compared. Can
                                 be either `xarray.DataArray` objects or
                                 identifiers to get the DataArrays from the
                                 current Scene. Defaults to all datasets.

        """
        warnings.warn(
            "'min_area' is deprecated, use 'coarsest_area' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.coarsest_area(datasets=datasets)

    def available_dataset_ids(self, reader_name=None, composites=False):
        """Get DataIDs of loadable datasets.

        This can be for all readers loaded by this Scene or just for
        ``reader_name`` if specified.

        Available dataset names are determined by what each individual reader
        can load. This is normally determined by what files are needed to load
        a dataset and what files have been provided to the scene/reader.
        Some readers dynamically determine what is available based on the
        contents of the files provided.

        By default, only returns non-composite dataset IDs.  To include
        composite dataset IDs, pass ``composites=True``.

        Args:
            reader_name (str, Optional): Name of reader for which to return
                dataset IDs.  If not passed, return dataset IDs for all
                readers.
            composites (bool, Optional): If True, return dataset IDs including
                composites.  If False (default), return only non-composite
                dataset IDs.

        Returns: list of available dataset IDs

        """
        try:
            if reader_name:
                readers = [self._readers[reader_name]]
            else:
                readers = self._readers.values()
        except (AttributeError, KeyError):
            raise KeyError("No reader '%s' found in scene" % reader_name)

        available_datasets = sorted([dataset_id
                                     for reader in readers
                                     for dataset_id in reader.available_dataset_ids])
        if composites:
            available_datasets += sorted(self.available_composite_ids())
        return available_datasets

    def available_dataset_names(self, reader_name=None, composites=False):
        """Get the list of the names of the available datasets.

        By default, this only shows names of datasets directly defined in (one
        of the) readers.  Names of composites are not returned unless the
        argument ``composites=True`` is passed.

        Args:
            reader_name (str, Optional): Name of reader for which to return
                dataset IDs.  If not passed, return dataset names for all
                readers.
            composites (bool, Optional): If True, return dataset IDs including
                composites.  If False (default), return only non-composite
                dataset names.

        Returns: list of available dataset names
        """
        return sorted(set(x["name"] for x in self.available_dataset_ids(
            reader_name=reader_name, composites=composites)))

    def all_dataset_ids(self, reader_name=None, composites=False):
        """Get IDs of all datasets from loaded readers or `reader_name` if specified.

        Excludes composites unless ``composites=True`` is passed.

        Args:
            reader_name (str, Optional): Name of reader for which to return
                dataset IDs.  If not passed, return dataset IDs for all
                readers.
            composites (bool, Optional): If True, return dataset IDs including
                composites.  If False (default), return only non-composite
                dataset IDs.

        Returns: list of all dataset IDs

        """
        try:
            if reader_name:
                readers = [self._readers[reader_name]]
            else:
                readers = self._readers.values()
        except (AttributeError, KeyError):
            raise KeyError("No reader '%s' found in scene" % reader_name)

        all_datasets = [dataset_id
                        for reader in readers
                        for dataset_id in reader.all_dataset_ids]
        if composites:
            all_datasets += self.all_composite_ids()
        return all_datasets

    def all_dataset_names(self, reader_name=None, composites=False):
        """Get all known dataset names configured for the loaded readers.

        Note that some readers dynamically determine what datasets are known
        by reading the contents of the files they are provided. This means
        that the list of datasets returned by this method may change depending
        on what files are provided even if a product/dataset is a "standard"
        product for a particular reader.

        Excludes composites unless ``composites=True`` is passed.

        Args:
            reader_name (str, Optional): Name of reader for which to return
                dataset IDs.  If not passed, return dataset names for all
                readers.
            composites (bool, Optional): If True, return dataset IDs including
                composites.  If False (default), return only non-composite
                dataset names.

        Returns: list of all dataset names

        """
        return sorted(set(x["name"] for x in self.all_dataset_ids(
            reader_name=reader_name, composites=composites)))

    def _check_known_composites(self, available_only=False):
        """Create new dependency tree and check what composites we know about."""
        # Note if we get compositors from the dep tree then it will include
        # modified composites which we don't want
        sensor_comps, mods = load_compositor_configs_for_sensors(self.sensor_names)
        # recreate the dependency tree so it doesn't interfere with the user's
        # wishlist from self._dependency_tree
        dep_tree = DependencyTree(self._readers, sensor_comps, mods, available_only=available_only)
        # ignore inline compositor dependencies starting with '_'
        comps = (comp for comp_dict in sensor_comps.values()
                 for comp in comp_dict.keys() if not comp["name"].startswith("_"))
        # make sure that these composites are even create-able by these readers
        all_comps = set(comps)
        # find_dependencies will update the all_comps set with DataIDs
        try:
            dep_tree.populate_with_keys(all_comps)
        except MissingDependencies:
            pass
        available_comps = set(x.name for x in dep_tree.trunk())
        # get rid of modified composites that are in the trunk
        return sorted(available_comps & all_comps)

    def available_composite_ids(self):
        """Get IDs of composites that can be generated from the available datasets."""
        return self._check_known_composites(available_only=True)

    def available_composite_names(self):
        """Names of all configured composites known to this Scene."""
        return sorted(set(x["name"] for x in self.available_composite_ids()))

    def all_composite_ids(self):
        """Get all IDs for configured composites."""
        return self._check_known_composites()

    def all_composite_names(self):
        """Get all names for all configured composites."""
        return sorted(set(x["name"] for x in self.all_composite_ids()))

    def all_modifier_names(self):
        """Get names of configured modifier objects."""
        return sorted(self._dependency_tree.modifiers.keys())

    def __str__(self):
        """Generate a nice print out for the scene."""
        res = (str(proj) for proj in self._datasets.values())
        return "\n".join(res)

    def __iter__(self):
        """Iterate over the datasets."""
        for x in self._datasets.values():
            yield x

    def iter_by_area(self):
        """Generate datasets grouped by Area.

        :return: generator of (area_obj, list of dataset objects)
        """
        datasets_by_area = {}
        for ds in self:
            a = ds.attrs.get("area")
            dsid = DataID.from_dataarray(ds)
            datasets_by_area.setdefault(a, []).append(dsid)

        return datasets_by_area.items()

    def keys(self, **kwargs):
        """Get DataID keys for the underlying data container."""
        return self._datasets.keys(**kwargs)

    def values(self):
        """Get values for the underlying data container."""
        return self._datasets.values()

    def _copy_datasets_and_wishlist(self, new_scn, datasets):
        for ds_id in datasets:
            # NOTE: Must use `._datasets` or side effects of `__setitem__`
            #       could hurt us with regards to the wishlist
            new_scn._datasets[ds_id] = self[ds_id]
        new_scn._wishlist = self._wishlist.copy()

    def copy(self, datasets=None):
        """Create a copy of the Scene including dependency information.

        Args:
            datasets (list, tuple): `DataID` objects for the datasets
                                    to include in the new Scene object.

        """
        new_scn = self.__class__()
        new_scn.attrs = self.attrs.copy()
        new_scn._dependency_tree = self._dependency_tree.copy()
        if datasets is None:
            datasets = self.keys()
        self._copy_datasets_and_wishlist(new_scn, datasets)
        return new_scn

    @property
    def all_same_area(self):
        """All contained data arrays are on the same area."""
        all_areas = [x.attrs.get("area", None) for x in self.values()]
        all_areas = [x for x in all_areas if x is not None]
        return all(all_areas[0] == x for x in all_areas[1:])

    @property
    def all_same_proj(self):
        """All contained data array are in the same projection."""
        all_areas = [x.attrs.get("area", None) for x in self.values()]
        all_areas = [x for x in all_areas if x is not None]
        return all(all_areas[0].crs == x.crs for x in all_areas[1:])

    @staticmethod
    def _slice_area_from_bbox(src_area, dst_area, ll_bbox=None,
                              xy_bbox=None):
        """Slice the provided area using the bounds provided."""
        if ll_bbox is not None:
            dst_area = AreaDefinition(
                "crop_area", "crop_area", "crop_latlong",
                {"proj": "latlong"}, 100, 100, ll_bbox)
        elif xy_bbox is not None:
            dst_area = AreaDefinition(
                "crop_area", "crop_area", "crop_xy",
                src_area.crs, src_area.width, src_area.height,
                xy_bbox)
        x_slice, y_slice = src_area.get_area_slices(dst_area)
        return src_area[y_slice, x_slice], y_slice, x_slice

    def _slice_datasets(self, dataset_ids, slice_key, new_area, area_only=True):
        """Slice scene in-place for the datasets specified."""
        new_datasets = {}
        datasets = (self[ds_id] for ds_id in dataset_ids)
        for ds, parent_ds in dataset_walker(datasets):
            ds_id = DataID.from_dataarray(ds)
            # handle ancillary variables
            pres = None
            if parent_ds is not None:
                parent_dsid = DataID.from_dataarray(parent_ds)
                pres = new_datasets[parent_dsid]
            if ds_id in new_datasets:
                replace_anc(ds, pres)
                continue
            if area_only and ds.attrs.get("area") is None:
                new_datasets[ds_id] = ds
                replace_anc(ds, pres)
                continue

            if not isinstance(slice_key, dict):
                # match dimension name to slice object
                key = dict(zip(ds.dims, slice_key))
            else:
                key = slice_key
            new_ds = ds.isel(**key)
            if new_area is not None:
                new_ds.attrs["area"] = new_area

            new_datasets[ds_id] = new_ds
            if parent_ds is None:
                # don't use `__setitem__` because we don't want this to
                # affect the existing wishlist/dep tree
                self._datasets[ds_id] = new_ds
            else:
                replace_anc(new_ds, pres)

    def slice(self, key):  # noqa: A003
        """Slice Scene by dataset index.

        .. note::

            DataArrays that do not have an ``area`` attribute will not be
            sliced.

        """
        if not self.all_same_area:
            raise RuntimeError("'Scene' has different areas and cannot "
                               "be usefully sliced.")
        # slice
        new_scn = self.copy()
        new_scn._wishlist = self._wishlist
        for area, dataset_ids in self.iter_by_area():
            if area is not None:
                # assume dimensions for area are y and x
                one_ds = self[dataset_ids[0]]
                area_key = tuple(sl for dim, sl in zip(one_ds.dims, key) if dim in ["y", "x"])
                new_area = area[area_key]
            else:
                new_area = None
            new_scn._slice_datasets(dataset_ids, key, new_area)
        return new_scn

    def crop(
            self,
            area: AreaDefinition | None = None,
            ll_bbox: tuple[float, float, float, float] | None = None,
            xy_bbox: tuple[float, float, float, float] | None = None,
            dataset_ids: Iterable | None = None,
    ) -> Scene:
        """Crop Scene to a specific Area boundary or bounding box.

        Args:
            area: Area to crop the current Scene to
            ll_bbox: 4-element tuple where values are in
                lon/lat degrees. Elements are
                ``(xmin, ymin, xmax, ymax)`` where X is
                longitude and Y is latitude.
            xy_bbox: Same as `ll_bbox` but elements are in projection units.
            dataset_ids: DataIDs to include in the returned `Scene`. Defaults to all datasets.

        This method will attempt to intelligently slice the data to preserve
        relationships between datasets. For example, if we are cropping two
        DataArrays of 500m and 1000m pixel resolution then this method will
        assume that exactly 4 pixels of the 500m array cover the same
        geographic area as a single 1000m pixel. It handles these cases based
        on the shapes of the input arrays and adjusting slicing indexes
        accordingly. This method will have trouble handling cases where data
        arrays seem related but don't cover the same geographic area or if the
        coarsest resolution data is not related to the other arrays which are
        related.

        It can be useful to follow cropping with a call to the native
        resampler to resolve all datasets to the same resolution and compute
        any composites that could not be generated previously::

        >>> cropped_scn = scn.crop(ll_bbox=(-105., 40., -95., 50.))
        >>> remapped_scn = cropped_scn.resample(resampler='native')

        .. note::

            The `resample` method automatically crops input data before
            resampling to save time/memory.

        """
        if len([x for x in [area, ll_bbox, xy_bbox] if x is not None]) != 1:
            raise ValueError("One and only one of 'area', 'll_bbox', "
                             "or 'xy_bbox' can be specified.")

        new_scn = self.copy(datasets=dataset_ids)
        if not new_scn.all_same_proj and xy_bbox is not None:
            raise ValueError("Can't crop when dataset_ids are not all on the "
                             "same projection.")

        # get the lowest resolution area, use it as the base of the slice
        # this makes sure that the other areas *should* be a consistent factor
        coarsest_area = new_scn.coarsest_area()
        if isinstance(area, str):
            area = get_area_def(area)
        new_coarsest_area, min_y_slice, min_x_slice = self._slice_area_from_bbox(
            coarsest_area, area, ll_bbox, xy_bbox)
        new_target_areas = {}
        for src_area, ids_on_area in new_scn.iter_by_area():
            if src_area is None:
                for ds_id in ids_on_area:
                    new_scn._datasets[ds_id] = self[ds_id]
                continue

            y_factor, y_remainder = np.divmod(float(src_area.shape[0]),
                                              coarsest_area.shape[0])
            x_factor, x_remainder = np.divmod(float(src_area.shape[1]),
                                              coarsest_area.shape[1])
            y_factor = int(y_factor)
            x_factor = int(x_factor)
            if y_remainder == 0 and x_remainder == 0:
                y_slice = slice(min_y_slice.start * y_factor,
                                min_y_slice.stop * y_factor)
                x_slice = slice(min_x_slice.start * x_factor,
                                min_x_slice.stop * x_factor)
                new_area = src_area[y_slice, x_slice]
                slice_key = {"y": y_slice, "x": x_slice}
                new_scn._slice_datasets(ids_on_area, slice_key, new_area)
            else:
                new_target_areas[src_area] = self._slice_area_from_bbox(
                    src_area, area, ll_bbox, xy_bbox
                )

        return new_scn

    def aggregate(self, dataset_ids=None, boundary="trim", side="left", func="mean", **dim_kwargs):
        """Create an aggregated version of the Scene.

        Args:
            dataset_ids (Iterable): DataIDs to include in the returned
                                    `Scene`. Defaults to all datasets.
            func (str, Callable): Function to apply on each aggregation window. One of
                           'mean', 'sum', 'min', 'max', 'median', 'argmin',
                           'argmax', 'prod', 'std', 'var' strings or a custom
                           function. 'mean' is the default.
            boundary: See :meth:`xarray.DataArray.coarsen`, 'trim' by default.
            side: See :meth:`xarray.DataArray.coarsen`, 'left' by default.
            dim_kwargs: the size of the windows to aggregate.

        Returns:
            A new aggregated scene

        See Also:
            xarray.DataArray.coarsen

        Example:
            `scn.aggregate(func='min', x=2, y=2)` will apply the `min` function
            across a window of size 2 pixels.

        """
        new_scn = self.copy(datasets=dataset_ids)

        for src_area, ds_ids in new_scn.iter_by_area():
            if src_area is None:
                for ds_id in ds_ids:
                    new_scn._datasets[ds_id] = self[ds_id]
                continue

            target_area = src_area.aggregate(boundary=boundary, **dim_kwargs)
            resolution = _get_area_resolution(target_area)
            for ds_id in ds_ids:
                new_scn._datasets[ds_id] = _aggregate_data_array(self[ds_id],
                                                                 func=func,
                                                                 boundary=boundary,
                                                                 side=side,
                                                                 **dim_kwargs)
                new_scn._datasets[ds_id].attrs = self[ds_id].attrs.copy()
                new_scn._datasets[ds_id].attrs["area"] = target_area
                new_scn._datasets[ds_id].attrs["resolution"] = resolution
        return new_scn

    def get(self, key, default=None):
        """Return value from DatasetDict with optional default."""
        return self._datasets.get(key, default)

    def __getitem__(self, key):
        """Get a dataset or create a new 'slice' of the Scene."""
        if isinstance(key, tuple):
            return self.slice(key)
        return self._datasets[key]

    def __setitem__(self, key, value):
        """Add the item to the scene."""
        self._datasets[key] = value
        # this could raise a KeyError but never should in this case
        ds_id = self._datasets.get_key(key)
        self._wishlist.add(ds_id)
        self._dependency_tree.add_leaf(ds_id)

    def __delitem__(self, key):
        """Remove the item from the scene."""
        k = self._datasets.get_key(key)
        self._wishlist.discard(k)
        del self._datasets[k]

    def __contains__(self, name):
        """Check if the dataset is in the scene."""
        return name in self._datasets

    def _slice_data(self, source_area, slices, dataset):
        """Slice the data to reduce it."""
        slice_x, slice_y = slices
        dataset = dataset.isel(x=slice_x, y=slice_y)
        if ("x", source_area.width) not in dataset.sizes.items():
            raise RuntimeError
        if ("y", source_area.height) not in dataset.sizes.items():
            raise RuntimeError
        dataset.attrs["area"] = source_area

        return dataset

    def _resampled_scene(self, new_scn, destination_area, reduce_data=True,
                         **resample_kwargs):
        """Resample `datasets` to the `destination` area.

        If data reduction is enabled, some local caching is perfomed in order to
        avoid recomputation of area intersections.
        """
        from satpy.resample.base import resample_dataset

        new_datasets = {}
        datasets = list(new_scn._datasets.values())
        destination_area = self._get_finalized_destination_area(destination_area, new_scn)

        resamplers = {}
        reductions = {}
        for dataset, parent_dataset in dataset_walker(datasets):
            ds_id = DataID.from_dataarray(dataset)
            pres = None
            if parent_dataset is not None:
                pres = new_datasets[DataID.from_dataarray(parent_dataset)]
            if ds_id in new_datasets:
                replace_anc(new_datasets[ds_id], pres)
                if ds_id in new_scn._datasets:
                    new_scn._datasets[ds_id] = new_datasets[ds_id]
                continue
            if dataset.attrs.get("area") is None:
                if parent_dataset is None:
                    new_scn._datasets[ds_id] = dataset
                else:
                    replace_anc(dataset, pres)
                continue
            LOG.debug("Resampling %s", ds_id)
            source_area = dataset.attrs["area"]
            dataset, source_area = self._reduce_data(dataset, source_area, destination_area,
                                                     reduce_data, reductions, resample_kwargs)
            self._prepare_resampler(source_area, destination_area, resamplers, resample_kwargs)
            kwargs = resample_kwargs.copy()
            kwargs["resampler"] = resamplers[source_area]
            res = resample_dataset(dataset, destination_area, **kwargs)
            new_datasets[ds_id] = res
            if ds_id in new_scn._datasets:
                new_scn._datasets[ds_id] = res
            if parent_dataset is not None:
                replace_anc(res, pres)

    def _get_finalized_destination_area(self, destination_area, new_scn):
        if isinstance(destination_area, str):
            destination_area = get_area_def(destination_area)
        if hasattr(destination_area, "freeze"):
            try:
                finest_area = new_scn.finest_area()
                destination_area = destination_area.freeze(finest_area)
            except ValueError:
                raise ValueError("No dataset areas available to freeze "
                                 "DynamicAreaDefinition.")
        return destination_area

    def _prepare_resampler(self, source_area, destination_area, resamplers, resample_kwargs):
        from satpy.resample.base import prepare_resampler

        if source_area not in resamplers:
            key, resampler = prepare_resampler(
                source_area, destination_area, **resample_kwargs)
            resamplers[source_area] = resampler
            self._resamplers[key] = resampler

    def _reduce_data(self, dataset, source_area, destination_area, reduce_data, reductions, resample_kwargs):
        try:
            if reduce_data:
                key = source_area
                try:
                    (slice_x, slice_y), source_area = reductions[key]
                except KeyError:
                    if resample_kwargs.get("resampler") == "gradient_search":
                        factor = resample_kwargs.get("shape_divisible_by", 2)
                    else:
                        factor = None
                    try:
                        slice_x, slice_y = source_area.get_area_slices(
                            destination_area, shape_divisible_by=factor)
                    except TypeError:
                        slice_x, slice_y = source_area.get_area_slices(
                            destination_area)
                    source_area = source_area[slice_y, slice_x]
                    reductions[key] = (slice_x, slice_y), source_area
                dataset = self._slice_data(source_area, (slice_x, slice_y), dataset)
            else:
                LOG.debug("Data reduction disabled by the user")
        except NotImplementedError:
            LOG.info("Not reducing data before resampling.")
        return dataset, source_area

    def resample(
            self,
            destination: AreaDefinition | CoordinateDefinition | None = None,
            datasets: Iterable | None = None,
            generate: bool = True,
            unload: bool = True,
            resampler: str | None = None,
            reduce_data: bool = True,
            **resample_kwargs,
    ) -> Scene:
        """Resample datasets and return a new scene.

        Args:
            destination: area definition to
                resample to. If not specified then the area returned by
                `Scene.finest_area()` will be used.
            datasets: Limit datasets to resample to these specified
                data arrays. By default all currently loaded
                datasets are resampled.
            generate: Generate any requested composites that could not
                be previously due to incompatible areas (default: True).
            unload: Remove any datasets no longer needed after
                requested composites have been generated (default: True).
            resampler: Name of resampling method to use. By default,
                this is a nearest neighbor KDTree-based resampling
                ('nearest'). Other possible values include 'native', 'ewa',
                etc. See the :mod:`~satpy.resample` documentation for more
                information.
            reduce_data: Reduce data by matching the input and output
                areas and slicing the data arrays (default: True)
            resample_kwargs: Remaining keyword arguments to pass to individual
                resampler classes. See the individual resampler class
                documentation :mod:`here <satpy.resample>` for available
                arguments.

        """
        if destination is None:
            destination = self.finest_area(datasets)
        new_scn = self.copy(datasets=datasets)
        self._resampled_scene(new_scn, destination, resampler=resampler,
                              reduce_data=reduce_data, **resample_kwargs)

        # regenerate anything from the wishlist that needs it (combining
        # multiple resolutions, etc.)
        if generate:
            new_scn.generate_possible_composites(unload)

        return new_scn

    def show(self, dataset_id, overlay=None):
        """Show the *dataset* on screen as an image.

        Show dataset on screen as an image, possibly with an overlay.

        Args:
            dataset_id (DataID, DataQuery or str):
                Either a DataID, a DataQuery or a string, that refers to a data
                array that has been previously loaded using Scene.load.
            overlay (dict, Optional):
                Add an overlay before showing the image.  The keys/values for
                this dictionary are as the arguments for
                :meth:`~satpy.enhancements.overlays.add_overlay`.  The dictionary should
                contain at least the key ``"coast_dir"``, which should refer
                to a top-level directory containing shapefiles.  See the
                pycoast_ package documentation for coastline shapefile
                installation instructions.

        .. _pycoast: https://pycoast.readthedocs.io/

        """
        from satpy.enhancements.enhancer import get_enhanced_image
        from satpy.utils import in_ipynb
        img = get_enhanced_image(self[dataset_id].squeeze(), overlay=overlay)
        if not in_ipynb():
            img.show()
        return img

    def to_geoviews(
            self,
            gvtype: Any | None = None,
            datasets: list | None = None,
            vdims: list[str] | None = None,
            dynamic: bool = False,
    ):
        """Convert satpy Scene to geoviews.

        Args:
            scn: Satpy Scene.
            gvtype:
                One of gv.Image, gv.LineContours, gv.FilledContours, gv.Points
                Default to ``geoviews.Image``.
                See Geoviews documentation for details.
            datasets: Limit included products to these datasets
            vdims:
                Value dimensions. See geoviews documentation for more information.
                If not given defaults to first data variable
            dynamic: Load and compute data on-the-fly during
                visualization. Default is ``False``. See
                https://holoviews.org/user_guide/Gridded_Datasets.html#working-with-xarray-data-types
                for more information. Has no effect when data to be visualized
                only has 2 dimensions (y/x or longitude/latitude) and doesn't
                require grouping via the Holoviews ``groupby`` function.

        Returns: geoviews object

        Todo:
            * better handling of projection information in datasets which are
              to be passed to geoviews

        """
        from satpy._scene_converters import to_geoviews
        return to_geoviews(self, gvtype=gvtype, datasets=datasets,
                           vdims=vdims, dynamic=dynamic)


    def to_hvplot(self, datasets=None, *args, **kwargs):
        """Convert satpy Scene to Hvplot. The method could not be used with composites of swath data.

        Args:
            scn (satpy.scene.Scene): Satpy Scene.
            datasets (list): Limit included products to these datasets.
            args: Arguments coming from hvplot
            kwargs: hvplot options dictionary.

        Returns:
            hvplot object that contains within it the plots of datasets list.
            As default it contains all Scene datasets plots and a plot title
            is shown.

        Example usage::

           scene_list = ['ash','IR_108']
           scn = Scene()
           scn.load(scene_list)
           scn = scn.resample('eurol')
           plot = scn.to_hvplot(datasets=scene_list)
           plot.ash+plot.IR_108
        """
        from satpy._scene_converters import to_hvplot

        return to_hvplot(self, datasets=None, *args, **kwargs)



    def to_xarray_dataset(self, datasets=None, compat="minimal"):
        """Merge all xr.DataArrays of a scene to a xr.DataSet.

        Parameters:
            datasets (list):
                List of products to include in the :class:`xarray.Dataset`
            compat (str):
                How to compare variables with the same name for conflicts.
                See :func:`xarray.merge` for possible options. Defaults to
                "minimal" which drops conflicting variables.

        Returns: :class:`xarray.Dataset`

        """
        from satpy._scene_converters import _get_dataarrays_from_identifiers

        dataarrays = _get_dataarrays_from_identifiers(self, datasets)

        if len(dataarrays) == 0:
            return xr.Dataset()

        ds_dict = {i.attrs["name"]: i.rename(i.attrs["name"]) for i in dataarrays if i.attrs.get("area") is not None}
        mdata = combine_metadata(*tuple(i.attrs for i in dataarrays))
        if mdata.get("area") is None or not isinstance(mdata["area"], SwathDefinition):
            # either don't know what the area is or we have an AreaDefinition
            ds = xr.merge(ds_dict.values(), compat=compat)
        else:
            # we have a swath definition and should use lon/lat values
            lons, lats = mdata["area"].get_lonlats()
            if not isinstance(lons, DataArray):
                lons = DataArray(lons, dims=("y", "x"))
                lats = DataArray(lats, dims=("y", "x"))
            ds = xr.Dataset(ds_dict, coords={"latitude": lats,
                                             "longitude": lons})

        ds.attrs = mdata
        return ds

    def to_xarray(
            self,
            datasets: Iterable | None = None,
            header_attrs: dict | None = None,
            exclude_attrs: Iterable | None = None,
            flatten_attrs: bool = False,
            pretty: bool = True,
            include_lonlats: bool = True,
            epoch: str | None = None,
            include_orig_name: bool = True,
            numeric_name_prefix: str = "CHANNEL_",
    ) -> xr.Datasaet:
        """Merge all xr.DataArray(s) of a satpy.Scene to a CF-compliant xarray object.

        If all Scene DataArrays are on the same area, it returns an xr.Dataset.
        If Scene DataArrays are on different areas, currently it fails, although
        in future we might return a DataTree object, grouped by area.

        Args:
            datasets:
                List of Satpy Scene datasets to include in the output xr.Dataset.
                Elements can be string name, a wavelength as a number, a DataID,
                or DataQuery object.
                If None (the default), it include all loaded Scene datasets.
            header_attrs:
                Global attributes of the output xr.Dataset.
            exclude_attrs:
                List of xr.DataArray attribute names to be excluded.
            flatten_attrs:
                If True, flatten dict-type attributes.
            pretty:
                Don't modify coordinate names, if possible. Makes the file prettier,
                but possibly less consistent.
            include_lonlats:
                If True, it includes 'latitude' and 'longitude' coordinates.
                If the 'area' attribute is a SwathDefinition, it always includes
                latitude and longitude coordinates.
            epoch:
                Reference time for encoding the time coordinates (if available).
                Example format: "seconds since 1970-01-01 00:00:00".
                If None, the default reference time is defined using "from satpy.cf.coords import EPOCH"
            include_orig_name:
                Include the original dataset name as a variable attribute in the xr.Dataset.
            numeric_name_prefix:
                Prefix to add the each variable with name starting with a digit.
                Use '' or None to leave this out.

        Returns:
            A CF-compliant xr.Dataset

        """
        from satpy._scene_converters import to_xarray

        return to_xarray(scn=self,
                         datasets=datasets,  # DataID
                         header_attrs=header_attrs,
                         exclude_attrs=exclude_attrs,
                         flatten_attrs=flatten_attrs,
                         pretty=pretty,
                         include_lonlats=include_lonlats,
                         epoch=epoch,
                         include_orig_name=include_orig_name,
                         numeric_name_prefix=numeric_name_prefix)

    def save_dataset(self, dataset_id, filename=None, writer=None,
                     overlay=None, decorate=None, compute=True, **kwargs):
        """Save the ``dataset_id`` to file using ``writer``.

        Args:
            dataset_id (str or numbers.Number or DataID or DataQuery): Identifier for
                the dataset to save to disk.
            filename (str): Optionally specify the filename to save this
                            dataset to. It may include string formatting
                            patterns that will be filled in by dataset
                            attributes.
            writer (str): Name of writer to use when writing data to disk.
                Default to ``"geotiff"``. If not provided, but ``filename`` is
                provided then the filename's extension is used to determine
                the best writer to use.
            overlay (dict): See :func:`satpy.enhancements.overlays.add_overlay`. Only valid
                for "image" writers like `geotiff` or `simple_image`.
            decorate (dict): See :func:`satpy.enhancements.overlays.add_decorate`. Only valid
                for "image" writers like `geotiff` or `simple_image`.
            compute (bool): If `True` (default), compute all of the saves to
                disk. If `False` then the return value is either a
                :doc:`dask:delayed` object or two lists to be passed to
                a `dask.array.store` call. See return values below for more
                details.
            kwargs: Additional writer arguments. See :doc:`../writing` for more
                information.

        Returns:
            Value returned depends on `compute`. If `compute` is `True` then
            the return value is the result of computing a
            :doc:`dask:delayed` object or running :func:`dask.array.store`.
            If `compute` is `False` then the returned value is either a
            :doc:`dask:delayed` object that can be computed using
            `delayed.compute()` or a tuple of (source, target) that should be
            passed to :func:`dask.array.store`. If target is provided the the
            caller is responsible for calling `target.close()` if the target
            has this method.

        """
        from satpy.writers.core.config import load_writer

        if writer is None and filename is None:
            writer = "geotiff"
        elif writer is None:
            writer = self._get_writer_by_ext(os.path.splitext(filename)[1])

        writer, save_kwargs = load_writer(writer,
                                          filename=filename,
                                          **kwargs)
        return writer.save_dataset(self[dataset_id],
                                   overlay=overlay, decorate=decorate,
                                   compute=compute, **save_kwargs)

    def save_datasets(self, writer=None, filename=None, datasets=None, compute=True,
                      **kwargs):
        """Save requested datasets present in a scene to disk using ``writer``.

        Note that dependency datasets (those loaded solely to create another
        and not requested explicitly) that may be contained in this Scene will
        not be saved by default. The default datasets are those explicitly
        requested through ``.load`` and exist in the Scene currently. Specify
        dependency datasets using the ``datasets`` keyword argument.

        Args:
            writer (str): Name of writer to use when writing data to disk.
                Default to ``"geotiff"``. If not provided, but ``filename`` is
                provided then the filename's extension is used to determine
                the best writer to use.
            filename (str): Optionally specify the filename to save this
                            dataset to. It may include string formatting
                            patterns that will be filled in by dataset
                            attributes.
            datasets (Iterable): Limit written products to these datasets.
                Elements can be string name, a wavelength as a number, a
                DataID, or DataQuery object.
            compute (bool): If `True` (default), compute all of the saves to
                disk. If `False` then the return value is either a
                :doc:`dask:delayed` object or two lists to be passed to
                a `dask.array.store` call. See return values below for more
                details.
            kwargs: Additional writer arguments. See :doc:`../writing` for more
                information.

        Returns:
            Value returned depends on `compute` keyword argument. If
            `compute` is `True` the value is the result of a either a
            `dask.array.store` operation or a :doc:`dask:delayed`
            compute, typically this is `None`. If `compute` is `False` then the
            result is either a :doc:`dask:delayed` object that can be
            computed with `delayed.compute()` or a two element tuple of
            sources and targets to be passed to :func:`dask.array.store`. If
            `targets` is provided then it is the caller's responsibility to
            close any objects that have a "close" method.

        """
        from satpy._scene_converters import _get_dataarrays_from_identifiers
        from satpy.writers.core.config import load_writer

        dataarrays = _get_dataarrays_from_identifiers(self, datasets)
        if not dataarrays:
            raise RuntimeError("None of the requested datasets have been "
                               "generated or could not be loaded. Requested "
                               "composite inputs may need to have matching "
                               "dimensions (eg. through resampling).")
        if writer is None:
            if filename is None:
                writer = "geotiff"
            else:
                writer = self._get_writer_by_ext(os.path.splitext(filename)[1])
        writer, save_kwargs = load_writer(writer,
                                          filename=filename,
                                          **kwargs)
        return writer.save_datasets(dataarrays, compute=compute, **save_kwargs)

    def compute(self, **kwargs):
        """Call `compute` on all Scene data arrays.

        See :meth:`xarray.DataArray.compute` for more details.
        Note that this will convert the contents of the DataArray to numpy arrays which
        may not work with all parts of Satpy which may expect dask arrays.
        """
        from dask import compute
        new_scn = self.copy()
        datasets = compute(*(new_scn._datasets.values()), **kwargs)

        for i, k in enumerate(new_scn._datasets.keys()):
            new_scn[k] = datasets[i]

        return new_scn

    def persist(self, **kwargs):
        """Call `persist` on all Scene data arrays.

        See :meth:`xarray.DataArray.persist` for more details.
        """
        from dask import persist
        new_scn = self.copy()
        datasets = persist(*(new_scn._datasets.values()), **kwargs)

        for i, k in enumerate(new_scn._datasets.keys()):
            new_scn[k] = datasets[i]

        return new_scn

    def chunk(self, **kwargs):
        """Call `chunk` on all Scene  data arrays.

        See :meth:`xarray.DataArray.chunk` for more details.
        """
        new_scn = self.copy()
        for k in new_scn._datasets.keys():
            new_scn[k] = new_scn[k].chunk(**kwargs)

        return new_scn

    @staticmethod
    def _get_writer_by_ext(extension):
        """Find the writer matching the ``extension``.

        Defaults to "simple_image".

        Example Mapping:

            - geotiff: .tif, .tiff
            - cf: .nc
            - mitiff: .mitiff
            - simple_image: .png, .jpeg, .jpg, ...

        Args:
            extension (str): Filename extension starting with
                "." (ex. ".png").

        Returns:
            str: The name of the writer to use for this extension.

        """
        mapping = {".tiff": "geotiff", ".tif": "geotiff", ".nc": "cf",
                   ".mitiff": "mitiff"}
        return mapping.get(extension.lower(), "simple_image")

    def _remove_failed_datasets(self, keepables):
        """Remove the datasets that we couldn't create."""
        # copy the set of missing datasets because they won't be valid
        # after they are removed in the next line
        missing = self.missing_datasets.copy()

        keepables = keepables or set()
        # remove reader datasets that couldn't be loaded so they aren't
        # attempted again later
        for n in self.missing_datasets:
            if n not in keepables:
                self._wishlist.discard(n)

        missing_str = ", ".join(str(x) for x in missing)
        LOG.warning("The following datasets were not created and may require "
                    "resampling to be generated: {}".format(missing_str))

    def unload(self, keepables=None):
        """Unload all unneeded datasets.

        Datasets are considered unneeded if they weren't directly requested
        or added to the Scene by the user or they are no longer needed to
        generate composites that have yet to be generated.

        Args:
            keepables (Iterable): DataIDs to keep whether they are needed
                                  or not.

        """
        to_del = [ds_id for ds_id, projectable in self._datasets.items()
                  if ds_id not in self._wishlist and (not keepables or ds_id
                                                      not in keepables)]
        for ds_id in to_del:
            LOG.debug("Unloading dataset: %r", ds_id)
            del self._datasets[ds_id]

    def load(self, wishlist, calibration="*", resolution="*",  # noqa: D417
             polarization="*", level="*", modifiers="*", generate=True, unload=True,
             **kwargs):
        """Read and generate requested datasets.

        When the `wishlist` contains `DataQuery` objects they can either be
        fully-specified `DataQuery` objects with every parameter specified
        or they can not provide certain parameters and the "best" parameter
        will be chosen. For example, if a dataset is available in multiple
        resolutions and no resolution is specified in the wishlist's DataQuery
        then the highest (the smallest number) resolution will be chosen.

        Loaded `DataArray` objects are created and stored in the Scene object.

        Args:
            wishlist (Iterable): List of names (str), wavelengths (float),
                DataQuery objects or DataID of the requested datasets to load.
                See `available_dataset_ids()` for what datasets are available.
            calibration (list | str): Calibration levels to limit available
                datasets. This is a shortcut to having to list each
                DataQuery/DataID in `wishlist`.
            resolution (list | float): Resolution to limit available datasets.
                This is a shortcut similar to calibration.
            polarization (list | str): Polarization ('V', 'H') to limit
                available datasets. This is a shortcut similar to calibration.
            modifiers (tuple | str): Modifiers that should be applied to the
                loaded datasets. This is a shortcut similar to calibration,
                but only represents a single set of modifiers as a tuple.
                For example, specifying
                ``modifiers=('sunz_corrected', 'rayleigh_corrected')`` will
                attempt to apply both of these modifiers to all loaded
                datasets in the specified order ('sunz_corrected' first).
            level (list | str): Pressure level to limit available datasets.
                Pressure should be in hPa or mb. If an altitude is used it
                should be specified in inverse meters (1/m). The units of this
                parameter ultimately depend on the reader.
            generate (bool): Generate composites from the loaded datasets
                (default: True)
            unload (bool): Unload datasets that were required to generate the
                requested datasets (composite dependencies) but are no longer
                needed.

        """
        if isinstance(wishlist, str):
            raise TypeError("'load' expects a list of datasets, got a string.")
        dataset_keys = set(wishlist)
        needed_datasets = (self._wishlist | dataset_keys) - set(self._datasets.keys())
        query = DataQuery(calibration=calibration,
                          polarization=polarization,
                          resolution=resolution,
                          modifiers=modifiers,
                          level=level)
        self._update_dependency_tree(needed_datasets, query)

        self._wishlist |= needed_datasets

        self._read_datasets_from_storage(**kwargs)
        if generate:
            self.generate_possible_composites(unload)

    def _update_dependency_tree(self, needed_datasets, query):
        try:
            comps, mods = load_compositor_configs_for_sensors(self.sensor_names)
            self._dependency_tree.update_compositors_and_modifiers(comps, mods)
            self._dependency_tree.populate_with_keys(needed_datasets, query)
        except MissingDependencies as err:
            raise KeyError(str(err))

    def _read_datasets_from_storage(self, **kwargs):
        """Load datasets from the necessary reader.

        Args:
            **kwargs: Keyword arguments to pass to the reader's `load` method.

        Returns:
            DatasetDict of loaded datasets

        """
        nodes = self._dependency_tree.leaves(limit_nodes_to=self.missing_datasets)
        return self._read_dataset_nodes_from_storage(nodes, **kwargs)

    def _read_dataset_nodes_from_storage(self, reader_nodes, **kwargs):
        """Read the given dataset nodes from storage."""
        # Sort requested datasets by reader
        reader_datasets = self._sort_dataset_nodes_by_reader(reader_nodes)
        loaded_datasets = self._load_datasets_by_readers(reader_datasets, **kwargs)
        self._datasets.update(loaded_datasets)
        return loaded_datasets

    def _sort_dataset_nodes_by_reader(self, reader_nodes):
        reader_datasets = {}
        for node in reader_nodes:
            ds_id = node.name
            # if we already have this node loaded or the node was assigned
            # by the user (node data is None) then don't try to load from a
            # reader
            if ds_id in self._datasets or not isinstance(node, ReaderNode):
                continue
            reader_name = node.reader_name
            if reader_name is None:
                # This shouldn't be possible
                raise RuntimeError("Dependency tree has a corrupt node.")
            reader_datasets.setdefault(reader_name, set()).add(ds_id)
        return reader_datasets

    def _load_datasets_by_readers(self, reader_datasets, **kwargs):
        # load all datasets for one reader at a time
        loaded_datasets = DatasetDict()
        for reader_name, ds_ids in reader_datasets.items():
            reader_instance = self._readers[reader_name]
            new_datasets = reader_instance.load(ds_ids, **kwargs)
            loaded_datasets.update(new_datasets)
        return loaded_datasets

    def generate_possible_composites(self, unload):
        """See which composites can be generated and generate them.

        Args:
            unload (bool): if the dependencies of the composites
                           should be unloaded after successful generation.
        """
        keepables = self._generate_composites_from_loaded_datasets()

        if self.missing_datasets:
            self._remove_failed_datasets(keepables)
        if unload:
            self.unload(keepables=keepables)

    def _filter_loaded_datasets_from_trunk_nodes(self, trunk_nodes):
        loaded_data_ids = self._datasets.keys()
        for trunk_node in trunk_nodes:
            if trunk_node.name in loaded_data_ids:
                continue
            yield trunk_node

    def _generate_composites_from_loaded_datasets(self):
        """Compute all the composites contained in `requirements`."""
        trunk_nodes = self._dependency_tree.trunk(limit_nodes_to=self.missing_datasets,
                                                  limit_children_to=self._datasets.keys())
        needed_comp_nodes = set(self._filter_loaded_datasets_from_trunk_nodes(trunk_nodes))
        return self._generate_composites_nodes_from_loaded_datasets(needed_comp_nodes)

    def _generate_composites_nodes_from_loaded_datasets(self, compositor_nodes):
        """Read (generate) composites."""
        keepables = set()
        for node in compositor_nodes:
            self._generate_composite(node, keepables)
        return keepables

    def _generate_composite(self, comp_node: CompositorNode, keepables: set):
        """Collect all composite prereqs and create the specified composite.

        Args:
            comp_node: Composite Node to generate a Dataset for
            keepables: `set` to update if any datasets are needed
                       when generation is continued later. This can
                       happen if generation is delayed to incompatible
                       areas which would require resampling first.

        """
        if self._datasets.contains(comp_node.name):
            # already loaded
            return

        compositor = comp_node.compositor
        prereqs = comp_node.required_nodes
        optional_prereqs = comp_node.optional_nodes

        try:
            delayed_prereq = False
            prereq_datasets = self._get_prereq_datasets(
                comp_node.name,
                prereqs,
                keepables,
            )
        except DelayedGeneration:
            # if we are missing a required dependency that could be generated
            # later then we need to wait to return until after we've also
            # processed the optional dependencies
            delayed_prereq = True
        except KeyError:
            # we are missing a hard requirement that will never be available
            # there is no need to "keep" optional dependencies
            return

        optional_datasets = self._get_prereq_datasets(
            comp_node.name,
            optional_prereqs,
            keepables,
            skip=True
        )

        # we are missing some prerequisites
        # in the future we may be able to generate this composite (delayed)
        # so we need to hold on to successfully loaded prerequisites and
        # optional prerequisites
        if delayed_prereq:
            preservable_datasets = set(self._datasets.keys())
            prereq_ids = set(p.name for p in prereqs)
            opt_prereq_ids = set(p.name for p in optional_prereqs)
            keepables |= preservable_datasets & (prereq_ids | opt_prereq_ids)
            return

        try:
            composite = compositor(prereq_datasets,
                                   optional_datasets=optional_datasets,
                                   **comp_node.name.to_dict())
            cid = DataID.new_id_from_dataarray(composite)
            self._datasets[cid] = composite

            # update the node with the computed DataID
            if comp_node.name in self._wishlist:
                self._wishlist.remove(comp_node.name)
                self._wishlist.add(cid)
            self._dependency_tree.update_node_name(comp_node, cid)
        except IncompatibleAreas:
            LOG.debug("Delaying generation of %s because of incompatible areas", str(compositor.id))
            preservable_datasets = set(self._datasets.keys())
            prereq_ids = set(p.name for p in prereqs)
            opt_prereq_ids = set(p.name for p in optional_prereqs)
            keepables |= preservable_datasets & (prereq_ids | opt_prereq_ids)
            # even though it wasn't generated keep a list of what
            # might be needed in other compositors
            keepables.add(comp_node.name)
            return

    def _get_prereq_datasets(self, comp_id, prereq_nodes, keepables, skip=False):
        """Get a composite's prerequisites, generating them if needed.

        Args:
            comp_id (DataID): DataID for the composite whose
                                 prerequisites are being collected.
            prereq_nodes (Sequence[Node]): Prerequisites to collect
            keepables (set): `set` to update if any prerequisites can't
                             be loaded at this time (see
                             `_generate_composite`).
            skip (bool): If True, consider prerequisites as optional and
                         only log when they are missing. If False,
                         prerequisites are considered required and will
                         raise an exception and log a warning if they can't
                         be collected. Defaults to False.

        Raises:
            KeyError: If required (skip=False) prerequisite can't be collected.

        """
        prereq_datasets = []
        delayed_gen = False
        for prereq_node in prereq_nodes:
            prereq_id = prereq_node.name
            if prereq_id not in self._datasets and prereq_id not in keepables \
                    and isinstance(prereq_node, CompositorNode):
                self._generate_composite(prereq_node, keepables)

            # composite generation may have updated the DataID
            prereq_id = prereq_node.name
            if prereq_node is self._dependency_tree.empty_node:
                # empty sentinel node - no need to load it
                continue
            elif prereq_id in self._datasets:
                prereq_datasets.append(self._datasets[prereq_id])
            elif isinstance(prereq_node, CompositorNode) and prereq_id in keepables:
                delayed_gen = True
                continue
            elif not skip:
                LOG.debug("Missing prerequisite for '{}': '{}'".format(
                    comp_id, prereq_id))
                raise KeyError("Missing composite prerequisite for"
                               " '{}': '{}'".format(comp_id, prereq_id))
            else:
                LOG.debug("Missing optional prerequisite for {}: {}".format(comp_id, prereq_id))

        if delayed_gen:
            keepables.add(comp_id)
            keepables.update([x.name for x in prereq_nodes])
            LOG.debug("Delaying generation of %s because of dependency's delayed generation: %s", comp_id, prereq_id)
            if not skip:
                LOG.debug("Delayed prerequisite for '{}': '{}'".format(comp_id, prereq_id))
                raise DelayedGeneration(
                    "Delayed composite prerequisite for "
                    "'{}': '{}'".format(comp_id, prereq_id))
            else:
                LOG.debug("Delayed optional prerequisite for {}: {}".format(comp_id, prereq_id))

        return prereq_datasets

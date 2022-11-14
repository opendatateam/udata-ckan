# Changelog

## Current (in progress)

- Nothing yet

## 3.0.0 (2022-11-14)

- :warning: **Breaking change** Use harvest dynamic field introduced in udata 5 [#227](https://github.com/opendatateam/udata-ckan/pull/227)

## 2.0.1 (2022-09-01)

- Replace mongo legacy image in CI [#219](https://github.com/opendatateam/udata-ckan/pull/219)
- Make revision_id optional to match latest CKAN versions [#220](https://github.com/opendatateam/udata-ckan/pull/220)

## 2.0.0 (2020-03-11)

- Migrate to python3 🐍 [#110](https://github.com/opendatateam/udata-ckan/pull/110)

## 1.3.0 (2020-01-06)

- DKAN support [#129](https://github.com/opendatateam/udata-ckan/pull/129)

## 1.2.3 (2019-05-29)

- Always fill extras.remote_url [#103](https://github.com/opendatateam/udata-ckan/pull/103)

## 1.2.2 (2019-05-24)

- Max out package_search rows limit [#100](https://github.com/opendatateam/udata-ckan/pull/98)

## 1.2.1 (2019-05-24)

- Fix filetype (always remote) [#98](https://github.com/opendatateam/udata-ckan/pull/98)

## 1.2.0 (2018-10-02)

- Support both inclusion and exclusion filters [#42](https://github.com/opendatateam/udata-ckan/pull/42)
- Localization support [#43](https://github.com/opendatateam/udata-ckan/pull/43)
- Test the minimum accepted CKAN dataset payload and make the `extras` property optional [#57](https://github.com/opendatateam/udata-ckan/pull/57)
- Improved error handling (support details in JSON responses, also handle raw quoted strings and HTML) [#56](https://github.com/opendatateam/udata-ckan/pull/56)

## 1.1.1 (2018-06-15)

- Only store `url` field in `remote_url` extra if this is an URL otherwise store it in `ckan:source` [#30](https://github.com/opendatateam/udata-ckan/pull/30)
- Properly handle geometry errors [#31](https://github.com/opendatateam/udata-ckan/pull/31)
- Improve extras parsing [#32](https://github.com/opendatateam/udata-ckan/pull/32):
  - Skip empty extras
  - Parse update frequencies as RDF URI or udata frequency identifier
  - Parse `spatial-text` matching a known zone name or slug
  - Store unknown `spatial-uri`, `spatial-text` and `frequency` as `ckan:spatial-uri`, `ckan:spatial-text` and `ckan:frequency`

## 1.1.0 (2018-06-06)

- Test against a real CKAN instance [#23](https://github.com/opendatateam/udata-ckan/pull/23)
- Allows to filter on Organizations and Tags [#26](https://github.com/opendatateam/udata-ckan/pull/26)
- Register `ckan:` prefixed extras [#28](https://github.com/opendatateam/udata-ckan/pull/28)

## 1.0.1 (2018-03-13)

- Fix packaging [#2](https://github.com/opendatateam/udata-ckan/pull/2)
- Make use of [udata pytest plugin](opendatateam/udata#1400) [#3](https://github.com/opendatateam/udata-ckan/pull/3)
- Enable the `ckan` plugin in test (plugin needs to be enabled to use the harvester) [#8](https://github.com/opendatateam/udata-ckan/pull/8)

## 1.0.0 (2017-10-20)

- Initial release

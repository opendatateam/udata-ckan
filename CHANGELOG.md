# Changelog

## Current (in progress)

- Migrate to python3 🐍 [#34](https://github.com/opendatateam/udata-ckan/pull/34)

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

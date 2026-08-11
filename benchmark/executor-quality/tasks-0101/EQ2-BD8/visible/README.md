# Rate-limit configuration fixture

The fixture models two-person administration of shared rate-limit rules. The limit writer owns rule inspection and persistence; the admin gate owns authorization decisions and their sequence.

Run the checks with:

```sh
node --test
```

# Iteration 06 sanitized inventory

**Identity:** I06-sanitized-v1. **Basis:** original H0 manifest, preserved unchanged. This inventory covers the verified nonsensitive subset of the original copied-file set; it does not claim that every file currently present under E4 is sanitized because the generated TLS certificate/private key remain pending researcher direction.

Included files: 77. Included bytes: 437819. Independently rehashed source/destination matches against the original manifest: 77/77. Mismatches: 0.

## Exclusions and resulting state

| Relative path | Reason/status |
|---|---|
| `deployment\.env.local` | Researcher-authorized E4-only file moved to protected external destination; absent from sanitized E4 tree. No value or content hash recorded. |
| `deployment\certs\dev-cert.pem` | Generated local TLS certificate excluded from the sanitized baseline; still present in E4 and E3, unchanged. No content/hash inspected. |
| `deployment\certs\dev-key.pem` | Generated local TLS private key excluded from the sanitized baseline; still present in E4 and E3, unchanged. No content/hash inspected. Further containment is not authorized by the `.env.local` approval. |

Generated `node_modules`, `dist`, caches, virtual environments, runtime databases/WAL/SHM, certificates/keys, and private runtime configuration are excluded. Retained paths are exactly the original manifest entries other than these three exclusions; each retained file was confirmed regular/non-reparse and rehashed against both the historical source and copied digests. The original manifest remains the record of initial copied state; this new manifest describes the post-containment sanitized subset. The TLS files are a remaining security exception, not a defect in retained source files.

## Retained paths

| Relative path | Bytes | Source SHA-256 | Sanitized destination SHA-256 | Match |
|---|---:|---|---|---|
| `.dockerignore` | 230 | `1fd04910f385d4dacc85d289de59be143e0e95c290f25a61a54eed6cd67f554d` | `1fd04910f385d4dacc85d289de59be143e0e95c290f25a61a54eed6cd67f554d` | yes |
| `backend\audit.py` | 11229 | `c371450705f68a1bb8e28339ea6204b9c71bf6c90fd97fb72a22d4add7123da1` | `c371450705f68a1bb8e28339ea6204b9c71bf6c90fd97fb72a22d4add7123da1` | yes |
| `backend\banking.py` | 39751 | `f78c05aa43c03e23dbafd742b654f67b291c8a1213614fa54488ee8ab4d8d685` | `f78c05aa43c03e23dbafd742b654f67b291c8a1213614fa54488ee8ab4d8d685` | yes |
| `backend\database.py` | 6071 | `4052f71d197599f14fb0acca84678ad2c4d55532206cc65813cc8909d4239f8d` | `4052f71d197599f14fb0acca84678ad2c4d55532206cc65813cc8909d4239f8d` | yes |
| `backend\encryption.py` | 7016 | `9446d3b28ed4161cad0b344a86147f4af0a524ba81d2ac2a2364f226a61b4116` | `9446d3b28ed4161cad0b344a86147f4af0a524ba81d2ac2a2364f226a61b4116` | yes |
| `backend\main.py` | 7783 | `0086a4180558b76c977af61e65c529c9b8ca7b34c8980b316e055d9d5d845f2f` | `0086a4180558b76c977af61e65c529c9b8ca7b34c8980b316e055d9d5d845f2f` | yes |
| `backend\requirements-loadtest.txt` | 35 | `8fda1228e32b9b59be1c44a6aade129cbe5ef0cb97e0bc6e45f5daac80a59874` | `8fda1228e32b9b59be1c44a6aade129cbe5ef0cb97e0bc6e45f5daac80a59874` | yes |
| `backend\requirements.txt` | 69 | `eb4b15ee08106740a3ed396e9ed465de758257db06a31c64590efd3022db8482` | `eb4b15ee08106740a3ed396e9ed465de758257db06a31c64590efd3022db8482` | yes |
| `backend\SECURITY.md` | 2857 | `a12b1cb0f4c859c2101ef0ed7dc03401aaf3ecdf57a8f43a4ce3b430ab6a4341` | `a12b1cb0f4c859c2101ef0ed7dc03401aaf3ecdf57a8f43a4ce3b430ab6a4341` | yes |
| `backend\loadtest\locustfile.py` | 4064 | `8f61ebe951b876d2c2a70f186aa4fd8fea22bba2d674023887771cb2f11a0a86` | `8f61ebe951b876d2c2a70f186aa4fd8fea22bba2d674023887771cb2f11a0a86` | yes |
| `backend\loadtest\metrics.py` | 1539 | `b9d7d87d647a1bbd7c6588a9719a4a7caeae125c70fdd2226c0c3969bf98125e` | `b9d7d87d647a1bbd7c6588a9719a4a7caeae125c70fdd2226c0c3969bf98125e` | yes |
| `backend\loadtest\run_benchmark.py` | 27325 | `0ec0e8467fa783470f71adf341a599e2f8ad01f5502424ccece58edc7288d333` | `0ec0e8467fa783470f71adf341a599e2f8ad01f5502424ccece58edc7288d333` | yes |
| `backend\loadtest\__init__.py` | 46 | `749c19bbaec5cc8ff2ab393d217b256a76e539bf6ac38ca7be6ed3326de1afa7` | `749c19bbaec5cc8ff2ab393d217b256a76e539bf6ac38ca7be6ed3326de1afa7` | yes |
| `backend\tests\test_api.py` | 9097 | `cf1106a0669e0454828dfcc105400a7c943d72340cb4dbe4e583a1e7916721a9` | `cf1106a0669e0454828dfcc105400a7c943d72340cb4dbe4e583a1e7916721a9` | yes |
| `backend\tests\test_audit.py` | 14744 | `2cee0cff756d4d075c383d2016371fc70f5d87e89f3046c67ea8c865bf4f024b` | `2cee0cff756d4d075c383d2016371fc70f5d87e89f3046c67ea8c865bf4f024b` | yes |
| `backend\tests\test_banking.py` | 25090 | `eac0c8174d9117ce1064bad7dd8fa0d50c8602631e6b9f3655ea85c95ae4d7fe` | `eac0c8174d9117ce1064bad7dd8fa0d50c8602631e6b9f3655ea85c95ae4d7fe` | yes |
| `backend\tests\test_encryption.py` | 11322 | `c8016dd92ef7c386128e1a1b846fc913b37e499a685ed207d6e3c67c475ea188` | `c8016dd92ef7c386128e1a1b846fc913b37e499a685ed207d6e3c67c475ea188` | yes |
| `backend\tests\test_loadtest_metrics.py` | 2947 | `8c86081df2bfa147de710b8444f7ef0685940c8714d75aa6623bf0b3b2da826b` | `8c86081df2bfa147de710b8444f7ef0685940c8714d75aa6623bf0b3b2da826b` | yes |
| `deployment\.env.example` | 299 | `879044f70a96adf3ab83b8503131371fb429dba234ab6c6a9104367a9def16e9` | `879044f70a96adf3ab83b8503131371fb429dba234ab6c6a9104367a9def16e9` | yes |
| `deployment\.gitignore` | 35 | `f52405f560ee8bca100eb4fc99817fb1cfef992421f4c211ab9fbccf168d56a0` | `f52405f560ee8bca100eb4fc99817fb1cfef992421f4c211ab9fbccf168d56a0` | yes |
| `deployment\backend.Dockerfile` | 858 | `0cd95004b1f90c796ef9215c40ee60eb798046e8b18fb017969bc7131a914930` | `0cd95004b1f90c796ef9215c40ee60eb798046e8b18fb017969bc7131a914930` | yes |
| `deployment\compose.yaml` | 2415 | `611d7c2d94ad037708d2b776fa57ce3d0b92e997683834f9acb2d7dc8c591c47` | `611d7c2d94ad037708d2b776fa57ce3d0b92e997683834f9acb2d7dc8c591c47` | yes |
| `deployment\frontend.Dockerfile` | 642 | `c472c7732ceea72a050df19a3f62f7f75621bfb39cb9185dd4dcf82478afd401` | `c472c7732ceea72a050df19a3f62f7f75621bfb39cb9185dd4dcf82478afd401` | yes |
| `deployment\generate_local_config.py` | 3026 | `f4efdc7b40d01d098b20918f0682a8d26102468e3be1f4366c57f1a321bd7366` | `f4efdc7b40d01d098b20918f0682a8d26102468e3be1f4366c57f1a321bd7366` | yes |
| `deployment\nginx.conf` | 1115 | `ad12fbe084bab55e217b4241cf8357e51c1d01832a3f54d727757bb2622a7215` | `ad12fbe084bab55e217b4241cf8357e51c1d01832a3f54d727757bb2622a7215` | yes |
| `deployment\README.md` | 3823 | `1dee775a23d2f6b577698f0dd11517b0fc0649b405c188b28ab3c86e8a0030c2` | `1dee775a23d2f6b577698f0dd11517b0fc0649b405c188b28ab3c86e8a0030c2` | yes |
| `deployment\verify_deployment.py` | 26724 | `eb196875df549d1bb153cdedee48347f9bc512b4c7e44ba969b74cd940e0cc80` | `eb196875df549d1bb153cdedee48347f9bc512b4c7e44ba969b74cd940e0cc80` | yes |
| `deployment\certs\.gitkeep` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | yes |
| `frontend\index.html` | 309 | `37da019d708db2ad7906a6682fae83a7641bcae04fcd71f6dcf05724294a17ee` | `37da019d708db2ad7906a6682fae83a7641bcae04fcd71f6dcf05724294a17ee` | yes |
| `frontend\package-lock.json` | 61019 | `180d36fb468650bae27601c6da29d53cacf79241c5d501c1a236c5866590d880` | `180d36fb468650bae27601c6da29d53cacf79241c5d501c1a236c5866590d880` | yes |
| `frontend\package.json` | 524 | `a61fc24b313e2e2015f80c2951204846f41bc7d139a08d4c54f04a3f5498514a` | `a61fc24b313e2e2015f80c2951204846f41bc7d139a08d4c54f04a3f5498514a` | yes |
| `frontend\tsconfig.json` | 575 | `37203e8f5ddeaea21d8755a6f4a0065466b2c74e526927e287e6e4421e9160e5` | `37203e8f5ddeaea21d8755a6f4a0065466b2c74e526927e287e6e4421e9160e5` | yes |
| `frontend\vite.config.ts` | 306 | `63968be3f2ff9f65c08eaea83c8676f6c3a6f2822a7c5b35b97c9c218d207f5d` | `63968be3f2ff9f65c08eaea83c8676f6c3a6f2822a7c5b35b97c9c218d207f5d` | yes |
| `frontend\src\api.d.mts` | 222 | `6597448680d217322ac8bff3dd07e4ac93916090bd60bf627f1c48fd405a316c` | `6597448680d217322ac8bff3dd07e4ac93916090bd60bf627f1c48fd405a316c` | yes |
| `frontend\src\api.mjs` | 858 | `0d1689088e12bf4bb60982763d5b3b798bb5dabd40763957690847ed646044a5` | `0d1689088e12bf4bb60982763d5b3b798bb5dabd40763957690847ed646044a5` | yes |
| `frontend\src\App.css` | 10463 | `cdb1589c231092232f4b0a972d9fe0b7975932242ca6e67ab03969542eed3f81` | `cdb1589c231092232f4b0a972d9fe0b7975932242ca6e67ab03969542eed3f81` | yes |
| `frontend\src\App.tsx` | 25770 | `90739219ae02c9f7df8fc7bc1f559112ced2ef5a3c26cca67bd57fcb782ed890` | `90739219ae02c9f7df8fc7bc1f559112ced2ef5a3c26cca67bd57fcb782ed890` | yes |
| `frontend\src\main.tsx` | 244 | `12599d6191d85cd1bf4a5be303a12f29c7d5c74590047a6f70025da989ef78b3` | `12599d6191d85cd1bf4a5be303a12f29c7d5c74590047a6f70025da989ef78b3` | yes |
| `frontend\src\refreshPolling.d.mts` | 91 | `3b45c84d44f7a5c28e747ded54a9f779d990d70350e4e3d0364da77d26e50849` | `3b45c84d44f7a5c28e747ded54a9f779d990d70350e4e3d0364da77d26e50849` | yes |
| `frontend\src\refreshPolling.mjs` | 177 | `2283c073467b0efd4ab0c347a9fa055d109f0423548f564b9284c02576ee5aea` | `2283c073467b0efd4ab0c347a9fa055d109f0423548f564b9284c02576ee5aea` | yes |
| `frontend\src\validation.d.mts` | 608 | `0115c7dddf46faa4d77e10d864d5beed5c4eb5f2d3934f5bf4b750d68af1e5be` | `0115c7dddf46faa4d77e10d864d5beed5c4eb5f2d3934f5bf4b750d68af1e5be` | yes |
| `frontend\src\validation.mjs` | 1784 | `de09b27a478a8287379f9680569ed2ee853c071d72f2e61c8ca7d1f072d6b0da` | `de09b27a478a8287379f9680569ed2ee853c071d72f2e61c8ca7d1f072d6b0da` | yes |
| `frontend\tests\button-types.test.mjs` | 1273 | `b09fe8265de39836ad5cd76fedd5250827a57115dba883346f3a840a7e043069` | `b09fe8265de39836ad5cd76fedd5250827a57115dba883346f3a840a7e043069` | yes |
| `frontend\tests\validation.test.mjs` | 4544 | `4e7d19f83b78f815a6303466159ffb67cde6dc8122e40ed7b0453db9d15cdd8d` | `4e7d19f83b78f815a6303466159ffb67cde6dc8122e40ed7b0453db9d15cdd8d` | yes |
| `openspec\config.yaml` | 922 | `2a791b0ccc50e2c2ebbb3ba28692a4ad0e4b6ab94ed2151375ac404d7056e89a` | `2a791b0ccc50e2c2ebbb3ba28692a4ad0e4b6ab94ed2151375ac404d7056e89a` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\.openspec.yaml` | 40 | `5edc88a042fdda2550686e54689bdd6779b13445bcaf782a1af9426634b9b4fb` | `5edc88a042fdda2550686e54689bdd6779b13445bcaf782a1af9426634b9b4fb` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\design.md` | 5821 | `b148610bb26906219fe26430d1e8b7df5281336b846e771964385b40566f0607` | `b148610bb26906219fe26430d1e8b7df5281336b846e771964385b40566f0607` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\proposal.md` | 2478 | `461956ffa07e924d08a16a082580bf17dc64ccf32aacd1ba6e1ed94490d5d523` | `461956ffa07e924d08a16a082580bf17dc64ccf32aacd1ba6e1ed94490d5d523` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\tasks.md` | 4022 | `9e4c878a5e64677b281d6cfaf254b87ecb0168a37b589329d9d21120b9a10e77` | `9e4c878a5e64677b281d6cfaf254b87ecb0168a37b589329d9d21120b9a10e77` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\specs\bank-accounts\spec.md` | 1325 | `006610469c6d0ba022d1d38fe8389263b315ecaaa3aabff94ef29236c4c64be5` | `006610469c6d0ba022d1d38fe8389263b315ecaaa3aabff94ef29236c4c64be5` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\specs\mfa\spec.md` | 2033 | `4b5a9968271383ed3b6a81d392dfc31f803b4d3d92480185a8ab44b5f56deb32` | `4b5a9968271383ed3b6a81d392dfc31f803b4d3d92480185a8ab44b5f56deb32` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\specs\transaction-history\spec.md` | 1223 | `d645648aef8346c17277d77bbe6bc3c967fdf6747742e822ffa4a8465005db4d` | `d645648aef8346c17277d77bbe6bc3c967fdf6747742e822ffa4a8465005db4d` | yes |
| `openspec\changes\archive\2026-09-29-stage1-requirements\specs\transfers\spec.md` | 2263 | `25fb7775581fbb867eff51377fd2980493c0f7940a8699962ae000178f23f129` | `25fb7775581fbb867eff51377fd2980493c0f7940a8699962ae000178f23f129` | yes |
| `openspec\changes\stage2-banking-enhancements\.openspec.yaml` | 40 | `db997d460a2d6d123d14faf903215b90f63faf4e7e2dadacfdab82c07857e113` | `db997d460a2d6d123d14faf903215b90f63faf4e7e2dadacfdab82c07857e113` | yes |
| `openspec\changes\stage2-banking-enhancements\design.md` | 10260 | `1f8c355f5ae71cb0b5929e6f7d18f8c232618ac86c721cf2584d6382e2aadc53` | `1f8c355f5ae71cb0b5929e6f7d18f8c232618ac86c721cf2584d6382e2aadc53` | yes |
| `openspec\changes\stage2-banking-enhancements\proposal.md` | 2961 | `a04cdedd43853cea6100498a2f99a86fd2d7fc2979aac7f6471e75489c227cfd` | `a04cdedd43853cea6100498a2f99a86fd2d7fc2979aac7f6471e75489c227cfd` | yes |
| `openspec\changes\stage2-banking-enhancements\tasks.md` | 9139 | `3e99e67bfe4630e087a835149371a0f5235409034c418df24b69c332056f8d64` | `3e99e67bfe4630e087a835149371a0f5235409034c418df24b69c332056f8d64` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\ach-transfers\spec.md` | 9352 | `cd735b36579aec20dd05b7c577d3aea584bf5c4891c2ef8593d333ee01f3bdbe` | `cd735b36579aec20dd05b7c577d3aea584bf5c4891c2ef8593d333ee01f3bdbe` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\bank-accounts\spec.md` | 1506 | `68fbcac20737908c61f622415b2fc2660a65111e82a5d6946002f559bf84da34` | `68fbcac20737908c61f622415b2fc2660a65111e82a5d6946002f559bf84da34` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\mfa\spec.md` | 3091 | `fb17de7974500ea7ce1c7f674b6eb650ba3acea2942483ba67bdb69fa2c8434e` | `fb17de7974500ea7ce1c7f674b6eb650ba3acea2942483ba67bdb69fa2c8434e` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\recurring-payments\spec.md` | 10931 | `6690404f0bffb2833724c65ef46350fb348002a183ec53b5ea5f2654b224dd1f` | `6690404f0bffb2833724c65ef46350fb348002a183ec53b5ea5f2654b224dd1f` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\transaction-history\spec.md` | 2269 | `248086af816d2eb7eb69ece72293f4add41562c352c58d2204dc5eb21f493158` | `248086af816d2eb7eb69ece72293f4add41562c352c58d2204dc5eb21f493158` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\transfer-limits\spec.md` | 6512 | `3b4922cb899f991b6b10f501c38a26cad01cb366f07f151eeb99809e5abcbba7` | `3b4922cb899f991b6b10f501c38a26cad01cb366f07f151eeb99809e5abcbba7` | yes |
| `openspec\changes\stage2-banking-enhancements\specs\transfers\spec.md` | 3833 | `4027cb768063644ec4ba0d0a86726f91f7c1ce892bf5125812a141ef47759103` | `4027cb768063644ec4ba0d0a86726f91f7c1ce892bf5125812a141ef47759103` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\.openspec.yaml` | 40 | `db997d460a2d6d123d14faf903215b90f63faf4e7e2dadacfdab82c07857e113` | `db997d460a2d6d123d14faf903215b90f63faf4e7e2dadacfdab82c07857e113` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\design.md` | 5819 | `cde81321efab051c9326b74eb67d32852ed08c59d9d027d3e1d83341b74aaca1` | `cde81321efab051c9326b74eb67d32852ed08c59d9d027d3e1d83341b74aaca1` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\proposal.md` | 2015 | `57c9ca0dad5152e081e86485968b4b3bfadfa009c75ab2388b2494a2e8d3df11` | `57c9ca0dad5152e081e86485968b4b3bfadfa009c75ab2388b2494a2e8d3df11` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\tasks.md` | 3536 | `42bd80d10d264d4fed809eb98956c786a0f02daa043f95cafd96695c70cc9cd0` | `42bd80d10d264d4fed809eb98956c786a0f02daa043f95cafd96695c70cc9cd0` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\specs\banking-compatibility\spec.md` | 3134 | `75ae2a6a275fd67a6c7b1baebaed5e9be9459924828992dd8a4e1389c1e00cf1` | `75ae2a6a275fd67a6c7b1baebaed5e9be9459924828992dd8a4e1389c1e00cf1` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\specs\banking-data-protection\spec.md` | 4691 | `69fc02165955b2b9717b0634b561fd654e0223c9f9fe7e8cdb31486f7dd6fd1d` | `69fc02165955b2b9717b0634b561fd654e0223c9f9fe7e8cdb31486f7dd6fd1d` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\specs\load-testing\spec.md` | 4336 | `31aac29e4a4b08c9b09dc8ca3d540572ec5b5f350ae9959b528a444500fc1fed` | `31aac29e4a4b08c9b09dc8ca3d540572ec5b5f350ae9959b528a444500fc1fed` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\specs\local-deployment\spec.md` | 3411 | `99f98eb8e725f10b34d30c4fdb286af8bd6460efe6b969953ae29b40abe4215e` | `99f98eb8e725f10b34d30c4fdb286af8bd6460efe6b969953ae29b40abe4215e` | yes |
| `openspec\changes\stage3-banking-security-load-deployment\specs\transaction-audit\spec.md` | 5064 | `7d7796b78b1a4c272292e52f3f825605fca5f3308683d9547f7c0d2d8e76b781` | `7d7796b78b1a4c272292e52f3f825605fca5f3308683d9547f7c0d2d8e76b781` | yes |
| `openspec\specs\bank-accounts\spec.md` | 1333 | `48d2e91a4b2bf8304de4a959f951abebc8ae3a659a79b939fdf0b0739e935e8c` | `48d2e91a4b2bf8304de4a959f951abebc8ae3a659a79b939fdf0b0739e935e8c` | yes |
| `openspec\specs\mfa\spec.md` | 2017 | `5835c0b208edbbb2ea17b296694499d1fa9b2aa47b10deffc462705fba34cf1b` | `5835c0b208edbbb2ea17b296694499d1fa9b2aa47b10deffc462705fba34cf1b` | yes |
| `openspec\specs\transaction-history\spec.md` | 1234 | `30f81ad0aabc8b6311fbfc48c6d2497e7f8d938f76f59be43da0040db5496a42` | `30f81ad0aabc8b6311fbfc48c6d2497e7f8d938f76f59be43da0040db5496a42` | yes |
| `openspec\specs\transfers\spec.md` | 2249 | `51a282ec9622f7770fa33d8902ad4a52d2fbb42528e28f23c2e7de648e2cbda9` | `51a282ec9622f7770fa33d8902ad4a52d2fbb42528e28f23c2e7de648e2cbda9` | yes |

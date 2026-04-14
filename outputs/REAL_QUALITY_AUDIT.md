# Real Quality Audit Report
**Generated:** 2026-04-14 08:15
**Products Audited:** 32

---

## Summary

| Grade | Count |
|-------|-------|
| 🟢 ELITE | 0 |
| 🟡 ACCEPTABLE | 0 |
| 🔴 BLOCKED | 32 |

---

## Detailed Results

| Product | Old Grade | Real Grade | Score | Authority | Relevance | Text Quality | Issues |
|---------|-----------|------------|-------|-----------|-----------|--------------|--------|
| sap-cloud-identity-services | ELITE | **BLOCKED** | 1.92 | 72% | 53% | 50% | 4 artifacts |
| sap-odata-performance | ELITE | **BLOCKED** | 1.91 | 65% | 59% | 50% | 5 artifacts |
| sap-successfactors-events | ELITE | **BLOCKED** | 1.87 | 63% | 58% | 50% | 4 artifacts |
| sap-event-mesh | ELITE | **BLOCKED** | 1.85 | 68% | 51% | 50% | 4 artifacts |
| sap-btp-basics | ELITE | **BLOCKED** | 1.84 | 61% | 57% | 50% | 5 artifacts |
| sap-build-process-automation | ELITE | **BLOCKED** | 1.83 | 61% | 56% | 50% | 3 artifacts |
| sap-b2b-integration | ELITE | **BLOCKED** | 1.82 | 67% | 49% | 50% | 5 artifacts |
| sap-analytics-cloud | ELITE | **BLOCKED** | 1.8 | 74% | 57% | 20% | 6 artifacts |
| sap-btp-resiliency | ELITE | **BLOCKED** | 1.8 | 68% | 29% | 80% | 1 wrong refs, 2 artifacts |
| sap-ai-core | ELITE | **BLOCKED** | 1.77 | 62% | 50% | 50% | 5 artifacts |
| sap-api-management | ELITE | **BLOCKED** | 1.75 | 73% | 53% | 20% | 6 artifacts |
| sap-datasphere | ELITE | **BLOCKED** | 1.75 | 61% | 48% | 50% | 3 artifacts |
| sap-btp-multitenant | ELITE | **BLOCKED** | 1.74 | 60% | 49% | 50% | 4 artifacts |
| sap-integration-migration | ELITE | **BLOCKED** | 1.74 | 52% | 57% | 50% | 5 artifacts, low auth sources |
| sap-federated-ml | ELITE | **BLOCKED** | 1.72 | 62% | 45% | 50% | 5 artifacts |
| sap-databricks | ELITE | **BLOCKED** | 1.69 | 51% | 53% | 50% | 5 artifacts, low auth sources |
| sap-edge-integration-cell | ELITE | **BLOCKED** | 1.68 | 48% | 55% | 50% | 5 artifacts, low auth sources |
| sap-secure-services | ELITE | **BLOCKED** | 1.66 | 64% | 54% | 20% | 6 artifacts |
| sap-devops | ELITE | **BLOCKED** | 1.65 | 69% | 49% | 20% | 6 artifacts |
| sap-master-data-integration | ELITE | **BLOCKED** | 1.65 | 47% | 70% | 20% | 7 artifacts, low auth sources |
| sap-btp-integration-suite | ELITE | **BLOCKED** | 1.64 | 56% | 60% | 20% | 7 artifacts, low auth sources |
| sap-hana-cloud | ELITE | **BLOCKED** | 1.64 | 57% | 59% | 20% | 6 artifacts, low auth sources |
| sap-private-link | ELITE | **BLOCKED** | 1.64 | 68% | 49% | 20% | 6 artifacts |
| sap-task-center | ELITE | **BLOCKED** | 1.62 | 67% | 47% | 20% | 7 artifacts |
| sap-build-work-zone | ELITE | **BLOCKED** | 1.61 | 62% | 51% | 20% | 7 artifacts |
| sap-joule | ELITE | **BLOCKED** | 1.59 | 59% | 35% | 50% | 2 wrong refs, 5 artifacts |
| sap-medallion-architecture | ELITE | **BLOCKED** | 1.57 | 47% | 46% | 50% | 5 artifacts, low auth sources |
| sap-s4hana-events | ELITE | **BLOCKED** | 1.55 | 60% | 48% | 20% | 6 artifacts, low auth sources |
| sap-siem-soar | ELITE | **BLOCKED** | 1.55 | 59% | 49% | 20% | 6 artifacts |
| sap-a2a-integration | ELITE | **BLOCKED** | 1.46 | 51% | 32% | 50% | 1 wrong refs, 5 artifacts, low auth sources |
| sap-cdp | ELITE | **BLOCKED** | 1.46 | 62% | 37% | 20% | 1 wrong refs, 6 artifacts |
| sap-b2g-integration | ELITE | **BLOCKED** | 1.44 | 64% | 33% | 20% | 1 wrong refs, 6 artifacts |

---

## Blocked Products - Detailed Issues

### sap-a2a-integration

**Wrong Product References:**
- Line 36: Found 'Auth0' in sap-a2a-integration doc

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'eOAu']
- OAuth concatenation: ['theOAuth', 'theOAuth', 'theOAuth']
- API concatenation: ['GoogleAPIs', 'GoogleAPIs', 'andAPIm']
- JSON concatenation: ['includingJSONS', 'includingJSONS', 'includingJSONS']
- Mid-sentence truncation: ['authenticationapik ... apiapi', 'changelog ... reference', 'Specificat ... leverage']

**Sources by Domain:**
- github.com: 2 refs (authority: 0.6)
- help.sap.com: 2 refs (authority: 1.0)
- milanjovanovic.tech: 1 refs (authority: 0.3)
- community.sap.com: 1 refs (authority: 0.7)
- integration-excellence.com: 1 refs (authority: 0.3)

### sap-ai-core

**Text Artifacts:**
- CamelCase concatenation: ['eAPIk', 'eOAu', 'aAPIc']
- OAuth concatenation: ['configureOAuth', 'ImplementOAuth', 'usingOAuth']
- API concatenation: ['simpleAPIk', 'ODataAPIc', 'secureAPIa']
- JSON concatenation: ['specifiedJSONs', 'exampleJSONi', 'exampleJSONi']
- Mid-sentence truncation: ['simpleAPIkey ... hentication', 'simpleAPIkey ... hentication', 'entit ... IforSAPAICore']

**Sources by Domain:**
- community.sap.com: 4 refs (authority: 0.7)
- help.sap.com: 3 refs (authority: 1.0)
- sap.github.io: 2 refs (authority: 0.3)
- sapexpert.ai: 1 refs (authority: 0.3)
- ieeexplore.ieee.org: 1 refs (authority: 0.3)

### sap-analytics-cloud

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eAPIs', 'wOAu']
- OAuth concatenation: ['theOAuth', 'howOAuth', 'theOAuth']
- API concatenation: ['theAPIs', 'GoogleCloudAPIswithAPIk', 'GoogleCloudAPIsuseAPIk']
- JSON concatenation: ['visualizeJSONs', 'visualizeJSONs', 'visualizeJSONs']
- codes concatenation: ['codesfrom', 'codesfrom', 'codestatus']

**Sources by Domain:**
- userapps.support.sap.com: 3 refs (authority: 0.3)
- help.sap.com: 3 refs (authority: 1.0)
- community.sap.com: 3 refs (authority: 0.7)
- scribd.com: 2 refs (authority: 0.3)
- cap.cloud.sap: 1 refs (authority: 0.3)

### sap-api-management

**Text Artifacts:**
- CamelCase concatenation: ['dAPIs', 'eOAu', 'eOAu']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'usingOAuth']
- API concatenation: ['exposedAPIs', 'yourAPIs', 'VerifyAPIK']
- JSON concatenation: ['usingJSONf', 'andOpenAPIJSONs', 'andOpenAPIJSONs']
- codes concatenation: ['codesthat', 'codescan', 'codesthat']

**Sources by Domain:**
- help.sap.com: 6 refs (authority: 1.0)
- community.sap.com: 5 refs (authority: 0.7)
- cleverence.com: 2 refs (authority: 0.3)
- sap.com: 1 refs (authority: 0.9)
- cdq.com: 1 refs (authority: 0.3)

### sap-b2b-integration

**Text Artifacts:**
- CamelCase concatenation: ['tAPIk', 'gAPIs', 'tAPIk']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'selectOAuth']
- API concatenation: ['aboutAPIk', 'securingAPIs', 'aboutAPIk']
- JSON concatenation: ['usingJSONf', 'OpenAPISpecJSONf']
- Mid-sentence truncation: ['securingAPIs ... enticationmethods', 'applic ... ovides', 'securingAPIs ... enticationmethods']

**Sources by Domain:**
- community.sap.com: 7 refs (authority: 0.7)
- help.sap.com: 4 refs (authority: 1.0)
- dev.to: 1 refs (authority: 0.3)
- topadvisor.com: 1 refs (authority: 0.3)
- cleverence.com: 1 refs (authority: 0.3)

### sap-b2g-integration

**Wrong Product References:**
- Line 38: Found 'Auth0' in sap-b2g-integration doc

**Text Artifacts:**
- CamelCase concatenation: ['eAPIs', 'eAPIu', 'eOAu']
- OAuth concatenation: ['TheOAuth', 'theOAuth', 'theOAuth']
- API concatenation: ['GoogleAPIs', 'GoogleAPIu', 'GoogleAPIs']
- JSON concatenation: ['usingJSONf', 'andOpenAPIJSONs', 'andJSONd']
- codes concatenation: ['codesthat', 'codesfrom', 'codesfrom']

**Sources by Domain:**
- community.sap.com: 4 refs (authority: 0.7)
- integration-excellence.com: 2 refs (authority: 0.3)
- sap.com: 2 refs (authority: 0.9)
- userapps.support.sap.com: 2 refs (authority: 0.3)
- getknit.dev: 1 refs (authority: 0.3)

### sap-btp-basics

**Text Artifacts:**
- CamelCase concatenation: ['nSAPBTPAPIMa', 'gAPIk', 'mAPIs']
- OAuth concatenation: ['withOAuth', 'withOAuth', 'withOAuth']
- API concatenation: ['inSAPBTPAPIM', 'ForauthenticationusingAPIk', 'PlatformAPIs']
- JSON concatenation: ['andJSONo', 'andJSONo']
- Mid-sentence truncation: ['obtai ... PlatformAPIsare', 'otherAPIswithi ... rAPIswithin', 'obtai ... PlatformAPIsare']

**Sources by Domain:**
- linkedin.com: 4 refs (authority: 0.2)
- community.sap.com: 2 refs (authority: 0.7)
- help.sap.com: 2 refs (authority: 1.0)
- assets.dm.ux.sap.com: 2 refs (authority: 0.3)
- qmacro.org: 1 refs (authority: 0.3)

### sap-btp-integration-suite

**Text Artifacts:**
- CamelCase concatenation: ['dOAu', 'rAPICl', 'nAPIc']
- OAuth concatenation: ['InboundOAuth', 'ExplaningOAuth', 'ExplaningOAuth']
- API concatenation: ['forAPIC', 'otherAPIs', 'forAPIC']
- JSON concatenation: ['andOpenAPIJSONs', 'andOpenAPIJSONs', 'andOpenAPIJSONs']
- HTTP concatenation: ['withHTTPS']

**Sources by Domain:**
- community.sap.com: 5 refs (authority: 0.7)
- github.com: 5 refs (authority: 0.6)
- linkedin.com: 2 refs (authority: 0.2)
- learning.scmgurus.com: 1 refs (authority: 0.3)
- securitybridge.com: 1 refs (authority: 0.3)

### sap-btp-multitenant

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'nAPIc']
- OAuth concatenation: ['ServiceOAuth', 'ServiceOAuth', 'requiresOAuth']
- API concatenation: ['otherAPIs', 'useAPIk', 'otherAPIs']
- Mid-sentence truncation: ['otherAPIswithi ... rAPIswithin', 'otherAPIswithi ... rAPIswithin', 'customr ... tingrules']

**Sources by Domain:**
- deepwiki.com: 2 refs (authority: 0.3)
- community.sap.com: 2 refs (authority: 0.7)
- github.com: 2 refs (authority: 0.6)
- sapintegrationhub.com: 1 refs (authority: 0.3)
- help.sap.com: 1 refs (authority: 1.0)

### sap-btp-resiliency

**Wrong Product References:**
- Line 36: Found 'Auth0' in sap-btp-resiliency doc

**Text Artifacts:**
- API concatenation: ['SAPAPIM']
- Mid-sentence truncation: ['SAPBTP... Addsap', 'SAPBTP... Addsap', 'paginatio... agination']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- community.sap.com: 3 refs (authority: 0.7)
- blogs.sap.com: 2 refs (authority: 0.65)
- levelup.gitconnected.com: 1 refs (authority: 0.3)
- stackoverflow.com: 1 refs (authority: 0.5)

### sap-build-process-automation

**Text Artifacts:**
- CamelCase concatenation: ['oSAPGe', 'oSAPGe', 'eAPIk']
- API concatenation: ['useAPIk', 'useAPIk', 'callprocessAPIo']
- Mid-sentence truncation: ['yourAPItrig ... scenario', 'forAPIGateway ... ControlAPIVisibility', 'forAPIGateway ... ControlAPIVisibility']

**Sources by Domain:**
- community.sap.com: 4 refs (authority: 0.7)
- github.com: 2 refs (authority: 0.6)
- leverx.com: 1 refs (authority: 0.3)
- help.sap.com: 1 refs (authority: 1.0)
- sap.com: 1 refs (authority: 0.9)

### sap-build-work-zone

**Text Artifacts:**
- CamelCase concatenation: ['yOAu', 'nSAPAPIMa', 'yOAu']
- OAuth concatenation: ['verifyOAuth', 'verifyOAuth', 'theOAuth']
- API concatenation: ['inSAPAPIM', 'otherAPIs', '0authenticationforAPIa']
- JSON concatenation: ['theJSONs', 'theJSONs', 'theJSONs']
- HTTP concatenation: ['returningHTTP4', 'returningHTTP4']

**Sources by Domain:**
- help.sap.com: 2 refs (authority: 1.0)
- learn.microsoft.com: 1 refs (authority: 0.8)
- buddysap.com: 1 refs (authority: 0.3)
- github.com: 1 refs (authority: 0.6)
- clusteringformeremortals.com: 1 refs (authority: 0.3)

### sap-cdp

**Wrong Product References:**
- Line 267: Found 'Twilio' in sap-cdp doc

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'eOAu']
- OAuth concatenation: ['TheOAuth', 'TheOAuth', 'TheOAuth']
- API concatenation: ['inSAPAPIM', 'FromAPIM', 'RESTAPIc']
- JSON concatenation: ['theJSONs']
- codes concatenation: ['codesfrom', 'codesfrom']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- community.sap.com: 3 refs (authority: 0.7)
- help.cdp.net: 1 refs (authority: 0.3)
- omr.com: 1 refs (authority: 0.3)
- buddysap.com: 1 refs (authority: 0.3)

### sap-cloud-identity-services

**Text Artifacts:**
- CamelCase concatenation: ['sAPIk', 'rSAPs', 'sAPIk']
- API concatenation: ['supportsAPIk', 'supportsAPIk', 'ThisAPIo']
- JSON concatenation: ['theJSONd', 'theJSONd']
- Mid-sentence truncation: ['theSAPCloudIdentityS ... sci_schema', 'predefinedschem ... chemasin', 'theSAPCloudIdentityS ... sci_schema']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- community.sap.com: 4 refs (authority: 0.7)
- github.com: 2 refs (authority: 0.6)
- api.sap.com: 1 refs (authority: 1.0)
- dev.to: 1 refs (authority: 0.3)

### sap-databricks

**Text Artifacts:**
- CamelCase concatenation: ['oSAPDa', 'gOAu', 'rOAu']
- OAuth concatenation: ['UsingOAuth', 'forOAuth', 'DatabricksusesOAuth']
- API concatenation: ['orDatabricksRESTAPIs', 'orDatabricksRESTAPIs', 'theDatabricksRESTAPIr']
- JSON concatenation: ['loadingJSONi', 'loadingJSONi']
- Mid-sentence truncation: ['AzureDatabr ... bricksendpoints', 'AzureDatabr ... bricksendpoints', 'perfor ... ervice']

**Sources by Domain:**
- community.sap.com: 3 refs (authority: 0.7)
- community.databricks.com: 2 refs (authority: 0.3)
- hevodata.com: 1 refs (authority: 0.3)
- userapps.support.sap.com: 1 refs (authority: 0.3)
- docs.databricks.com: 1 refs (authority: 0.3)

### sap-datasphere

**Text Artifacts:**
- CamelCase concatenation: ['eSAPDa', 'nAPIs', 'nOAu']
- API concatenation: ['theSAPDatasphereConsumptionAPIs', 'ARIBAAPIi', 'CloudAPIU']
- Mid-sentence truncation: ['Underst ... rocess', 'Underst ... rocess', 'serve ... demonstrate']

**Sources by Domain:**
- community.sap.com: 4 refs (authority: 0.7)
- userapps.support.sap.com: 3 refs (authority: 0.3)
- linkedin.com: 2 refs (authority: 0.2)
- github.com: 2 refs (authority: 0.6)
- epiuselabs.com: 1 refs (authority: 0.3)

### sap-devops

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'rAPIs']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'theOAuth']
- API concatenation: ['yourAPIs', 'SAPAPIO', 'yourAPIs']
- JSON concatenation: ['andJSONe']
- HTTP concatenation: ['MasterHTTPS', 'MasterHTTPS', 'UnderstandingHTTPs']

**Sources by Domain:**
- community.sap.com: 4 refs (authority: 0.7)
- help.sap.com: 4 refs (authority: 1.0)
- learn.microsoft.com: 2 refs (authority: 0.8)
- stackoverflow.com: 2 refs (authority: 0.5)
- support.ariba.com: 1 refs (authority: 0.3)

### sap-edge-integration-cell

**Text Artifacts:**
- CamelCase concatenation: ['nOAu', 'nOAu', 'nOAu']
- OAuth concatenation: ['Register_an_OAuth']
- API concatenation: ['OpenAPIJ', 'OpenAPIJ', 'OpenAPIJ']
- JSON concatenation: ['OpenAPIJSONs', 'OpenAPIJSONs', 'OpenAPIJSONs']
- Mid-sentence truncation: ['usage ... imensions', 'usage ... imensions', 'offsetpa ... xplore']

**Sources by Domain:**
- linkedin.com: 2 refs (authority: 0.2)
- help.sap.com: 2 refs (authority: 1.0)
- sp.ts.fujitsu.com: 1 refs (authority: 0.3)
- integration-excellence.com: 1 refs (authority: 0.3)
- github.com: 1 refs (authority: 0.6)

### sap-event-mesh

**Text Artifacts:**
- CamelCase concatenation: ['nOAu', 'eOAu', 'gURLo']
- OAuth concatenation: ['TheOAuth']
- API concatenation: ['individualAPIe', 'RESTAPIt', 'advancedeventmeshappliesAPIr']
- Mid-sentence truncation: ['requests ... Receive', 'requests ... Receive', 'RESTAPIthat ... either']

**Sources by Domain:**
- help.pubsub.em.services.cloud.sap: 4 refs (authority: 0.3)
- help.sap.com: 4 refs (authority: 1.0)
- learning.sap.com: 3 refs (authority: 0.3)
- community.sap.com: 3 refs (authority: 0.7)
- blogs.sap.com: 3 refs (authority: 0.65)

### sap-federated-ml

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'rAPIs']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'ConfigureOAuth']
- API concatenation: ['yourAPIs', 'inSAPAPIM', 'secureSAPAPIO']
- codes concatenation: ['codesthat', 'codesand', 'codesthat']
- Mid-sentence truncation: ['applic ... ovides', 'applic ... ovides', 'Sockets ... including']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- nagarro.com: 1 refs (authority: 0.3)
- learning.sap.com: 1 refs (authority: 0.3)
- ieeexplore.ieee.org: 1 refs (authority: 0.3)
- openai.com: 1 refs (authority: 0.3)

### sap-hana-cloud

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eSAPHANAd', 'eOAu']
- OAuth concatenation: ['useOAuth', 'evaluateOAuth', 'usingOAuth']
- API concatenation: ['secureSAPAPIO', 'yourAPIc', '0RESTAPIc']
- JSON concatenation: ['maintainingJSONd']
- codes concatenation: ['codesfor', 'codesfor', 'codesfor']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- wiki.eclipse.org: 2 refs (authority: 0.3)
- userapps.support.sap.com: 2 refs (authority: 0.3)
- linkedin.com: 2 refs (authority: 0.2)
- community.sap.com: 2 refs (authority: 0.7)

### sap-integration-migration

**Text Artifacts:**
- CamelCase concatenation: ['yOAu', 'nOAu', 'yOAu']
- OAuth concatenation: ['implementOAuth', 'usingOAuth', 'usingOAuth']
- API concatenation: ['viaSAPAPIM', 'secureSAPAPIO', 'theAPIp']
- JSON concatenation: ['SpecJSONf', 'OpenAPIJSONs', 'intoJSONf']
- Mid-sentence truncation: ['actually ... actually', 'CloudIntegratio ... yintegrationflows', 'usage ... imensions']

**Sources by Domain:**
- help.sap.com: 3 refs (authority: 1.0)
- sapintegrationhub.com: 2 refs (authority: 0.3)
- lnkd.in: 1 refs (authority: 0.3)
- community.sap.com: 1 refs (authority: 0.7)
- linkedin.com: 1 refs (authority: 0.2)

### sap-joule

**Wrong Product References:**
- Line 35: Found 'Auth0' in sap-joule doc
- Line 36: Found 'Gmail' in sap-joule doc

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'lAPIr']
- OAuth concatenation: ['theOAuth', 'theOAuth', 'TheOAuth']
- API concatenation: ['GmailAPIr', 'GmailAPIr', 'theAPIm']
- JSON concatenation: ['AdoptJSONS', 'AdoptJSONS', 'GenerateJSONS']
- Mid-sentence truncation: ['GenerateJSONSchemade ... ONSchemaOnline', 'relevant ... Thesecurityguide', 'relevant ... Thesecurityguide']

**Sources by Domain:**
- sap.com: 2 refs (authority: 0.9)
- sap.github.io: 1 refs (authority: 0.3)
- help.sap.com: 1 refs (authority: 1.0)
- community.sap.com: 1 refs (authority: 0.7)
- zequance.ai: 1 refs (authority: 0.3)

### sap-master-data-integration

**Text Artifacts:**
- CamelCase concatenation: ['tOAu', 'mAPIMa', 'eOAu']
- OAuth concatenation: ['selectOAuth', 'ConfigureOAuth', 'withOAuth']
- API concatenation: ['CloudIntegrationFromAPIM', 'inSAPAPIM', 'SAPAPIO']
- JSON concatenation: ['OpenAPIJSONs', 'OpenAPIJSONs', 'OpenAPIJSONs']
- HTTP concatenation: ['activateHTTPS', 'leveragingHTTPS', 'forHTTPS']

**Sources by Domain:**
- linkedin.com: 2 refs (authority: 0.2)
- cleverence.com: 2 refs (authority: 0.3)
- learn.microsoft.com: 1 refs (authority: 0.8)
- github.com: 1 refs (authority: 0.6)
- sapintegrationhub.com: 1 refs (authority: 0.3)

### sap-medallion-architecture

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'rAPIs']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'usingOAuth']
- API concatenation: ['yourAPIs', 'secureSAPAPIO', '0RESTAPIc']
- HTTP concatenation: ['activateHTTPS']
- Mid-sentence truncation: ['applic ... ovides', 'applic ... ovides', 'frequency ... ThrottlingThrottlingplaces']

**Sources by Domain:**
- community.sap.com: 3 refs (authority: 0.7)
- docs.medallion.co: 2 refs (authority: 0.3)
- linkedin.com: 2 refs (authority: 0.2)
- bluefunda.com: 1 refs (authority: 0.3)
- github.com: 1 refs (authority: 0.6)

### sap-odata-performance

**Text Artifacts:**
- CamelCase concatenation: ['nAPIk', 'nAPIk', 'eAPIk']
- OAuth concatenation: ['withOAuth', 'usingOAuth']
- API concatenation: ['APIkeyauthenticationAPIk', 'APIkeyauthenticationAPIk', 'uniqueAPIk']
- JSON concatenation: ['toODataJSONF', 'theODataJSONp', 'toODataJSONF']
- Mid-sentence truncation: ['uniqueAPIkey ... APIkeyau', 'uniqueAPIkey ... APIkeyauthenticationrequires', 'implem ... annotations']

**Sources by Domain:**
- help.sap.com: 3 refs (authority: 1.0)
- community.sap.com: 3 refs (authority: 0.7)
- linkedin.com: 2 refs (authority: 0.2)
- en.wikipedia.org: 1 refs (authority: 0.3)
- avotechs.com: 1 refs (authority: 0.3)

### sap-private-link

**Text Artifacts:**
- CamelCase concatenation: ['eSAPAPIODa', 'gOAu', 'eOAu']
- OAuth concatenation: ['usingOAuth', 'ConfigureOAuth', 'ImplementOAuth']
- API concatenation: ['secureSAPAPIO', 'inSAPAPIM', 'secureAPIa']
- JSON concatenation: ['JSONJSONF', 'JSONJSONF', 'JSONJSONF']
- codes concatenation: ['codesfor', 'codesfor', 'codestudy']

**Sources by Domain:**
- github.com: 3 refs (authority: 0.6)
- help.sap.com: 3 refs (authority: 1.0)
- community.sap.com: 3 refs (authority: 0.7)
- learn.microsoft.com: 1 refs (authority: 0.8)
- aws.amazon.com: 1 refs (authority: 0.3)

### sap-s4hana-events

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'aAPIc', 'gOAu']
- OAuth concatenation: ['configureOAuth', '4HANAOAuth', 'ConfiguringOAuth']
- API concatenation: ['ODataAPIc', 'oAuth2APId', 'ODataAPIc']
- JSON concatenation: ['provideJSONs', 'provideJSONs', 'provideJSONs']
- codes concatenation: ['codesfor', 'codesfor', 'codesfor']

**Sources by Domain:**
- help.sap.com: 3 refs (authority: 1.0)
- sapintegrationhub.com: 2 refs (authority: 0.3)
- community.sap.com: 2 refs (authority: 0.7)
- scribd.com: 2 refs (authority: 0.3)
- rollout.com: 1 refs (authority: 0.3)

### sap-secure-services

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'rAPIs']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'withOAuth']
- API concatenation: ['yourAPIs', 'SAPAPIO', 'externalAPIs']
- JSON concatenation: ['usesJSONp', 'usingJSONf', 'authoritativeJSONS']
- codes concatenation: ['codesthat', 'codesand', 'codesand']

**Sources by Domain:**
- help.sap.com: 3 refs (authority: 1.0)
- linkedin.com: 2 refs (authority: 0.2)
- community.sap.com: 2 refs (authority: 0.7)
- learning.sap.com: 2 refs (authority: 0.3)
- medium.com: 1 refs (authority: 0.4)

### sap-siem-soar

**Text Artifacts:**
- CamelCase concatenation: ['eOAu', 'eOAu', 'rAPIs']
- OAuth concatenation: ['TheOAuth', 'configureOAuth', 'usingOAuth']
- API concatenation: ['yourAPIs', 'secureSAPAPIO', 'externalAPIs']
- JSON concatenation: ['theJSONs', 'theJSONs', 'theJSONs']
- codes concatenation: ['codesand', 'codeslike', 'codesand']

**Sources by Domain:**
- help.sap.com: 3 refs (authority: 1.0)
- medium.com: 2 refs (authority: 0.4)
- userapps.support.sap.com: 2 refs (authority: 0.3)
- techcommunity.microsoft.com: 1 refs (authority: 0.3)
- natuvion.com: 1 refs (authority: 0.3)

### sap-successfactors-events

**Text Artifacts:**
- CamelCase concatenation: ['rAPIa', 'hOAu', 'wOAu']
- OAuth concatenation: ['WithOAuth', 'howOAuth', 'integrateSAPSuccessFactorsOAuth']
- API concatenation: ['0authenticationforAPIa', 'secureAPIa', '0authenticationforAPIa']
- Mid-sentence truncation: ['provider ... rocess', 'provider ... rocess', 'standard ... SuccessFactorsrequires']

**Sources by Domain:**
- userapps.support.sap.com: 4 refs (authority: 0.3)
- community.sap.com: 2 refs (authority: 0.7)
- help.sap.com: 2 refs (authority: 1.0)
- rollout.com: 2 refs (authority: 0.3)
- elearningindustry.com: 1 refs (authority: 0.3)

### sap-task-center

**Text Artifacts:**
- CamelCase concatenation: ['eSAPTa', 'rAPIUs', 'eSAPTa']
- OAuth concatenation: ['withOAuth', 'withOAuth', 'callSAPTaskCenterAPIsusingOAuth']
- API concatenation: ['theSAPTaskCenterAPIU', 'TheSAPTaskCenterAPIi', 'callSAPTaskCenterAPIs']
- JSON concatenation: ['interactiveJSONS', 'SupportsJSONS', 'interactiveJSONS']
- HTTP concatenation: ['activateHTTPS', 'activateHTTPS', 'activateHTTPS']

**Sources by Domain:**
- help.sap.com: 4 refs (authority: 1.0)
- community.sap.com: 2 refs (authority: 0.7)
- userapps.support.sap.com: 2 refs (authority: 0.3)
- codestudy.net: 1 refs (authority: 0.3)
- thecfoclub.com: 1 refs (authority: 0.3)


---

## Methodology

This audit checks:
1. **Source Authority** - Are evidence sources from official documentation?
2. **Product Relevance** - Does evidence actually reference the target product?
3. **Text Quality** - Are there concatenation/truncation artifacts?
4. **URL Validity** - Do source links work? (if --verify-urls)

Unlike the broken regex-only checker, this validates actual content quality.
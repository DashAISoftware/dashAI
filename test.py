import requests

""" 
select_types: Annotated[Union[List[str], None], Query()], optional
    If specified, the function return only the components that extend the
    provided types (e.g., task, model, dataloader, etc...).
    If None, the method returns all components in the registry, by default None.
ignore_types: Annotated[Union[List[str], None], Query()], optional
    If specified, the function return every components that is not that extend
    the provided types (e.g., task, model, dataloader, etc...).
    If None, the method returns all components in the registry, by default None.
related_component : Union[str , None], optional
    If specified, the function return only the components related with
    the specified compatible component, (usually some task. as
    TabularClassification, Translation, etc.), by default None.
component_parent : Union[str , None], optional
    If specified, the function return only the components that inheirts the
    indicated component (e.g., ScikitLearnLikeModel), by default None.
has_related_of_type : Union[str, None], optional
    If specified, the function returns only components that have at least one
    related component of the specified type (e.g., "Model"). This is useful for
    filtering tasks that have associated models, by default None.
component_registry : ComponentRegistry
    The current app component registry provided by dependency injection. """

#print("related component: RAGTask")
#print(requests.get("http://localhost:8000/api/v1/component/?related_component=RAGTask").json())
#print()

import json

#response = requests.get("http://localhost:8000/api/v1/component/?select_types=Model&component_parent=RetrieverModel").json()
#for r in response:
#    print(json.dumps(r, indent=2))
#
#print()
#print()
#print()
#print()
#print()
#
#response = requests.get("http://localhost:8000/api/v1/component/?select_types=Model&related_component=RAGTask").json()
#for r in response:
#    print(json.dumps(r, indent=2))
#
#print()
#print()
#print()
#print()
#print()


queries = [
    #"component/Embedding",
    #"component/RAGPipeline",
    "component/RetrieverModel/children",
    #"component/?component_parent=Encoding",
    #"component/SparseRetriever/children/",
    "component/DenseRetriever/",
    "component/TFIDFRetriever/"

]
print()

for q in queries:
    print(q)
    response = requests.get(f"http://localhost:8000/api/v1/{q}")
    print(json.dumps(response.json(), indent=2))
    print()
    print()
    print()
 


#ESTA WEA NO FUNCIONA
#input()
#print("related component: Model, component parent: RetrieverModel")
#response = requests.get("http://localhost:8000/api/v1/component/?related_component=Model&component_parent=RetrieverModel").json()
#print(response)
#print()

#ESTA WEA TAMPOCO
#input()
#print("related component: [Model, RetrieverModel ]")
#response = requests.get("http://localhost:8000/api/v1/component/?related_component=RAGTask&related_component=RetrieverModel").json()
#print(response)


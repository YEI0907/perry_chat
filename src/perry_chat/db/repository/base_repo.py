from typing import Generic, Type, TypeVar, List, Optional, Union

from tortoise.models import Model

# 使用泛型来定义模型的类型
ModelType = TypeVar("ModelType", bound=Model)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, pk: Union[int, str]) -> Optional[ModelType]:
        return await self.model.get_or_none(id=pk)

    async def get_all(self) -> List[ModelType]:
        return await self.model.all()

    async def create(self, **kwargs) -> ModelType:
        return await self.model.create(**kwargs)

    async def update(self, pk: Union[int, str], **kwargs) -> Optional[ModelType]:
        obj = await self.get(pk)
        if obj:
            await obj.update_from_dict(kwargs).save()
            return obj
        return None

    async def delete(self, pk: Union[int, str]) -> bool:
        obj = await self.get(pk)
        if obj:
            await obj.delete()
            return True
        return False

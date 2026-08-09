from abc import ABC, abstractmethod


class DataProvider(ABC):

    @abstractmethod
    async def get_vessels_in_area(
        self,
        lon_left: float,
        lon_right: float,
        lat_bottom: float,
        lat_top: float,
    ):
        pass
import pytest

from geonoderest.resources import GeonodeResourceHandler
from geonoderest.apiconf import GeonodeApiConf
class TestResource:
  
  def setup_class(self):
      conf = GeonodeApiConf.from_env_vars()
      self.gn_resources_handler = GeonodeResourceHandler(conf)

  def test_list_getresources(self):
      r = self.gn_resources_handler.list()
      assert isinstance(r, list)
      
  
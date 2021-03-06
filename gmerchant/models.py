from django.db import models
from django.utils.text import slugify

from local_shop.catalogue.models import Product

from .client import ShoppingClient
#p12-key_pw = notasecret

def key_upload(instance,filename):
    return "/".join(['uploads','temp','keys',slugify(instance.application_name),filename])

class APIServiceCredentials(models.Model):
        """
        This model is used for configuring the credentials required for communicating with the G-API.
        """
        application_name = models.CharField(max_length=256)

        client_id = models.CharField(max_length=128)
        client_email = models.EmailField(blank=True,max_length=128)

        private_key_file = models.FileField(upload_to=key_upload,help_text="This is deleted immediately after reading and encrypting.",blank=True,null=True)

        private_key_ciphertext = models.TextField(blank=True)
        private_key_phrase = models.CharField(max_length=512,help_text="This isn't stored in plaintext after saving.",blank=True)

        def __unicode__(self):
            return self.application_name

class GoogleMerchantAccount(models.Model):
        account_name = models.CharField(max_length=128)
        account_id = models.CharField(max_length=64)

        credentials = models.ForeignKey('APIServiceCredentials',null=True,blank=True)

        catalogue_imported = models.BooleanField(default=True)


        client = None

        def __unicode__(self):
            return self.account_name + " " + self.account_id

        def init_client(self):
            if not self.client:
                self.client = ShoppingClient(app=self)

        def fetch_catalogue(self):
            self.init_client()
            self.client.listProducts()

        def insert_test(self):
            #This is for testing.
            p = GoogleProduct.objects.filter(publish_google_shopping=True,
                                       stockrecords__num_in_stock__gte=1)
            if p:
                self.insert_product(p[0])

        def insert_product(self,product):
            self.init_client()
            if product.in_stock:
                self.client.insertProduct(product)
            else:
                raise AttributeError("This product is not available to be purchased")

        def upload_catalogue(self):
            self.init_client()
            # Grab products that aren't already on Google.
            p = GoogleProduct.objects.filter(publish_google_shopping=True,
                                       product__stockrecords__num_in_stock__gte=1).exclude(google_shopping_id!=None)
                                       
            if len(p) > 0:
                self.client.batchInsertProducts(p)
            else:
                raise ValueError("There aren't any products that are suitable to upload")
                
        def refresh_catalogue(self):
            self.init_client()
            # Grab all products that are already on Google.
            p = GoogleProduct.objects.filter(publish_google_shopping=True,
                                       product__stockrecords__num_in_stock__gte=1).exclude(google_shopping_id=None)
                                       
            if len(p) > 0:
                self.client.batchInsertProducts(p)
            else:
                raise ValueError("There aren't any products that are suitable to upload")

        def update_inventory(self):
            self.init_client()
            p = GoogleProduct.objects.all().select_related()
            if len(p) > 0:
                self.client.batchUpdate(p)
            else:
                raise ValueError("There aren't any products that are suitable for updating")


class GoogleCategory(models.Model):
    name = models.CharField(max_length=512)
    source_idx = models.IntegerField(db_index=True)

    def __unicode__(self):
        return self.name


class GoogleProduct(models.Model):
    class Meta:
        verbose_name = "Google Merchant Records"
        verbose_name_plural = "Google Merchant Records"

    product = models.ForeignKey(Product)

    publish_google_shopping = models.BooleanField(default=False)
    google_taxonomy = models.ForeignKey("gmerchant.GoogleCategory",blank=True,null=True)
    google_shopping_description = models.TextField(null=True, blank=True)

    product_upc = models.CharField(max_length=32,blank=True,null=True,db_index=True,editable=False)
    google_shopping_id = models.CharField(max_length=128,blank=True,null=True,db_index=True)
    google_shopping_created = models.DateTimeField(blank=True,null=True)
    google_shopping_updated = models.DateTimeField(blank=True,null=True)

    def __unicode__(self):
        return str(self.product.upc) or "" + " - " + self.google_shopping_id or ""



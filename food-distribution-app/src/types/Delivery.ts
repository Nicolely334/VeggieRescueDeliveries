export type Delivery = {
  id: string;
  delivery_date: string;
  recipient: string;
  location: string;
  produce_pounds: number | null;
  packaged_pounds: number | null;
  driver: string;
  vehicle: string;
  status: string;
};
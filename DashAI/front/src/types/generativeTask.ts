import type { IParameterJsonSchema } from "./configurableObject";

export type GenerativeInputType = "str" | "Image" | "Audio" | "Video" | string;
export type CardinalityRange = { min: number; max: number | "n" };
export type Cardinality = number | "n" | CardinalityRange;
export type CardinalityMap = Partial<Record<GenerativeInputType, Cardinality>>;

export interface IGenerativeTask {
  name: string;
  type: string;
  configurable_object: boolean;
  schema: IParameterJsonSchema | null;
  metadata: {
    inputs: CardinalityMap;
    outputs: CardinalityMap;
  };
  description: string;
  display_name: string;
  color: string | null;
  downloaded?: boolean;
}

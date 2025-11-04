import { useEffect, useState } from "react";
import {
  AcceptReject,
  ExtractedDataDisplay,
  FilePreview,
  useItemData,
  type Highlight,
  Button,
} from "@llamaindex/ui";
import { Clock, XCircle, Download } from "lucide-react";
import { useParams } from "react-router-dom";
import { useToolbar } from "@/lib/ToolbarContext";
import { useNavigate } from "react-router-dom";
import { modifyJsonSchema } from "@llamaindex/ui/lib";
import { APP_TITLE } from "@/lib/config";
import { downloadExtractedDataItem } from "@/lib/export";
import { useMetadataContext } from "@/lib/MetadataProvider";

export default function ItemPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const { setButtons, setBreadcrumbs } = useToolbar();
  const [highlight, setHighlight] = useState<Highlight | undefined>(undefined);
  const { metadata } = useMetadataContext();

  // Use the hook to fetch item data (initially with a default schema)
  const itemHookData = useItemData<any>({
    // We'll update the schema based on classification once data loads
    jsonSchema: modifyJsonSchema(metadata.schemas["10-K"] || {}, {}),
    itemId: itemId as string,
    isMock: false,
  });

  // Determine the correct schema based on classification
  const classification = (
    (itemHookData.item?.data?.metadata?.classification as string | undefined) ||
    "10-K"
  ).toUpperCase();
  const correctSchema =
    metadata.schemas[classification] || metadata.schemas["10-K"];

  // Update the schema in itemHookData if classification is available
  const [schemaKey, setSchemaKey] = useState(0);
  const [appliedSchema, setAppliedSchema] = useState(correctSchema);

  useEffect(() => {
    if (classification && metadata.schemas[classification]) {
      setAppliedSchema(modifyJsonSchema(metadata.schemas[classification], {}));
      setSchemaKey(schemaKey + 1);
    }
  }, [classification, metadata.schemas]);

  const navigate = useNavigate();

  // Update breadcrumb when item data loads
  useEffect(() => {
    const fileName = itemHookData.item?.data?.file_name;
    if (fileName) {
      setBreadcrumbs([
        { label: APP_TITLE, href: "/" },
        {
          label: fileName,
          isCurrentPage: true,
        },
      ]);
    }

    return () => {
      // Reset to default breadcrumb when leaving the page
      setBreadcrumbs([{ label: APP_TITLE, href: "/" }]);
    };
  }, [itemHookData.item?.data?.file_name, setBreadcrumbs]);

  useEffect(() => {
    setButtons(() => [
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (itemData) {
              downloadExtractedDataItem(itemData);
            }
          }}
          disabled={!itemData}
        >
          <Download className="h-4 w-4 mr-2" />
          Export JSON
        </Button>
        <AcceptReject<any>
          itemData={itemHookData}
          onComplete={() => navigate("/")}
        />
      </div>,
    ]);
    return () => {
      setButtons(() => []);
    };
  }, [itemHookData.data, setButtons]);

  const {
    item: itemData,
    updateData,
    loading: isLoading,
    error,
  } = itemHookData;

  const classificationReasoning = itemData?.data?.metadata
    ?.classification_reasoning as string | undefined;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
          <div className="text-sm text-gray-500">Loading item...</div>
        </div>
      </div>
    );
  }

  if (error || !itemData) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <div className="text-sm text-gray-500">
            Error loading item: {error || "Item not found"}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-gray-50">
      {/* Left Side - File Preview */}
      <div className="w-1/2 border-r border-gray-200 bg-white">
        {itemData.data.file_id && (
          <FilePreview
            fileId={itemData.data.file_id}
            onBoundingBoxClick={(box, pageNumber) => {
              console.log("Bounding box clicked:", box, "on page:", pageNumber);
            }}
            highlight={highlight}
          />
        )}
      </div>

      {/* Right Side - Review Panel */}
      <div className="flex-1 bg-white h-full overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Classification Info */}
          {classification && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <div className="text-sm font-semibold text-blue-900">
                Document Type: {classification}
              </div>
              {classificationReasoning && (
                <div className="text-xs text-blue-600 mt-1">
                  {classificationReasoning}
                </div>
              )}
            </div>
          )}
          {/* Extracted Data */}
          <ExtractedDataDisplay<any>
            key={schemaKey}
            extractedData={itemData.data}
            title="Extracted Data"
            onChange={(updatedData) => {
              updateData(updatedData);
            }}
            onClickField={(args) => {
              // TODO: set multiple highlights
              setHighlight({
                page: args.metadata?.citation?.[0]?.page ?? 1,
                x: 100,
                y: 100,
                width: 0,
                height: 0,
              });
            }}
            jsonSchema={appliedSchema}
          />
        </div>
      </div>
    </div>
  );
}

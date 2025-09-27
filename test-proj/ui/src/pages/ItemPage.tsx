import { useEffect, useState } from "react";
import {
  AcceptReject,
  ExtractedDataDisplay,
  FilePreview,
  useItemData,
  type Highlight,
} from "@llamaindex/ui";
import { Clock, XCircle } from "lucide-react";
import { useParams } from "react-router-dom";
import type { MySchema } from "../schemas/MySchema";
import MyJsonSchema from "../schemas/MySchema.json" with { type: "json" };
import { useToolbar } from "@/lib/ToolbarContext";
import { useNavigate } from "react-router-dom";
import { modifyJsonSchema } from "@llamaindex/ui/lib";
import { APP_TITLE } from "@/lib/config";

export default function ItemPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const { setButtons, setBreadcrumbs } = useToolbar();
  const [highlight, setHighlight] = useState<Highlight | undefined>(undefined);

  // Use the hook to fetch item data
  const itemHookData = useItemData<MySchema>({
    // order/remove fields as needed here
    jsonSchema: modifyJsonSchema(MyJsonSchema as any, {}),
    itemId: itemId as string,
    isMock: false,
  });

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
      <div className="ml-auto flex items-center">
        <AcceptReject<MySchema>
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
          {/* Extracted Data */}
          <ExtractedDataDisplay<MySchema>
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
            jsonSchema={itemHookData.jsonSchema}
          />
        </div>
      </div>
    </div>
  );
}

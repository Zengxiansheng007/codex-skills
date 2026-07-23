# Release change cases

## Project workspace

### Item management

#### Item list / Create item

##### tc-P0:Create item requires Name

###### Step 1: Click the "Create item" button on the Item list page
* Expected: The "Create item" dialog is opened and the "Name" field is visible
###### Step 2: Leave the "Name" field empty and click the "Save" button
* Expected: The "Name is required" validation message is shown and no item is created
* rc: Source: SRC-001
